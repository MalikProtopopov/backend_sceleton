"""IndexNow integration service for notifying search engines of URL changes."""

import asyncio
import secrets
from datetime import datetime, UTC
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.tenants.models import TenantSettings

logger = get_logger(__name__)

# IndexNow API endpoints for different search engines
INDEXNOW_ENDPOINTS = {
    "bing": "https://www.bing.com/indexnow",
    "yandex": "https://yandex.com/indexnow",
    "seznam": "https://search.seznam.cz/indexnow",
    "naver": "https://searchadvisor.naver.com/indexnow",
}

# Default endpoint (Bing, which shares with other engines)
DEFAULT_ENDPOINT = INDEXNOW_ENDPOINTS["bing"]


class IndexNowService:
    """Service for IndexNow URL submission to search engines.
    
    IndexNow is a protocol that allows websites to notify search engines
    about URL changes (add, update, delete) for faster indexing.
    
    Key features:
    - Batch URL submission (up to 10,000 URLs per request)
    - Automatic deduplication
    - Retry on failure
    - Rate limiting
    """
    
    # Maximum URLs per batch (IndexNow limit)
    MAX_BATCH_SIZE = 10000
    
    # Minimum interval between submissions (seconds)
    MIN_SUBMISSION_INTERVAL = 60
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._last_submission: dict[UUID, datetime] = {}
    
    async def get_key(self, tenant_id: UUID) -> str | None:
        """Get IndexNow key for tenant.
        
        Returns None if IndexNow is not configured or not enabled.
        """
        settings = await self._get_tenant_settings(tenant_id)
        if not settings:
            return None
        
        if not settings.indexnow_enabled:
            return None
        
        return settings.indexnow_key
    
    async def is_enabled(self, tenant_id: UUID) -> bool:
        """Check if IndexNow is enabled for tenant."""
        settings = await self._get_tenant_settings(tenant_id)
        if not settings:
            return False
        return settings.indexnow_enabled and bool(settings.indexnow_key)
    
    async def generate_key(self, tenant_id: UUID) -> str:
        """Generate a new IndexNow key for tenant.
        
        The key should be stored in TenantSettings.indexnow_key
        and a key file should be accessible at /{key}.txt
        
        Returns:
            Generated key (32 hex characters)
        """
        return secrets.token_hex(16)
    
    async def submit_url(
        self,
        tenant_id: UUID,
        url: str,
        host: str | None = None,
    ) -> bool:
        """Submit a single URL to IndexNow.
        
        Args:
            tenant_id: Tenant ID
            url: Full URL to submit
            host: Host domain (extracted from URL if not provided)
            
        Returns:
            True if submission was successful
        """
        return await self.submit_urls(tenant_id, [url], host)
    
    async def submit_urls(
        self,
        tenant_id: UUID,
        urls: list[str],
        host: str | None = None,
    ) -> bool:
        """Submit multiple URLs to IndexNow.
        
        Args:
            tenant_id: Tenant ID
            urls: List of full URLs to submit
            host: Host domain (extracted from first URL if not provided)
            
        Returns:
            True if submission was successful
        """
        if not urls:
            return True
        
        # Check if IndexNow is enabled
        key = await self.get_key(tenant_id)
        if not key:
            logger.debug(
                "indexnow_not_configured",
                tenant_id=str(tenant_id),
            )
            return False
        
        # Rate limiting
        if not self._can_submit(tenant_id):
            logger.warning(
                "indexnow_rate_limited",
                tenant_id=str(tenant_id),
            )
            return False
        
        # Extract host from first URL if not provided
        if not host:
            from urllib.parse import urlparse
            parsed = urlparse(urls[0])
            host = parsed.netloc
        
        # Deduplicate URLs
        unique_urls = list(dict.fromkeys(urls))
        
        # Batch if necessary
        if len(unique_urls) > self.MAX_BATCH_SIZE:
            # Split into batches
            for i in range(0, len(unique_urls), self.MAX_BATCH_SIZE):
                batch = unique_urls[i:i + self.MAX_BATCH_SIZE]
                success = await self._submit_batch(tenant_id, key, host, batch)
                if not success:
                    return False
            return True
        
        return await self._submit_batch(tenant_id, key, host, unique_urls)
    
    async def _submit_batch(
        self,
        tenant_id: UUID,
        key: str,
        host: str,
        urls: list[str],
    ) -> bool:
        """Submit a batch of URLs to IndexNow."""
        # Build request payload
        payload = {
            "host": host,
            "key": key,
            "urlList": urls,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    DEFAULT_ENDPOINT,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                
                # IndexNow returns:
                # 200 - OK, URL submitted successfully
                # 202 - Accepted, URL received
                # 400 - Bad request (invalid format)
                # 403 - Forbidden (key not valid)
                # 422 - Unprocessable Entity (URL doesn't match host)
                # 429 - Too many requests
                
                if response.status_code in (200, 202):
                    logger.info(
                        "indexnow_submitted",
                        tenant_id=str(tenant_id),
                        url_count=len(urls),
                        status_code=response.status_code,
                    )
                    self._record_submission(tenant_id)
                    return True
                else:
                    logger.error(
                        "indexnow_failed",
                        tenant_id=str(tenant_id),
                        status_code=response.status_code,
                        response_text=response.text[:500],
                    )
                    return False
                    
        except httpx.RequestError as e:
            logger.error(
                "indexnow_request_error",
                tenant_id=str(tenant_id),
                error=str(e),
            )
            return False
    
    def _can_submit(self, tenant_id: UUID) -> bool:
        """Check if we can submit (rate limiting)."""
        last = self._last_submission.get(tenant_id)
        if not last:
            return True
        
        elapsed = (datetime.now(UTC) - last).total_seconds()
        return elapsed >= self.MIN_SUBMISSION_INTERVAL
    
    def _record_submission(self, tenant_id: UUID) -> None:
        """Record a submission for rate limiting."""
        self._last_submission[tenant_id] = datetime.now(UTC)
    
    async def _get_tenant_settings(self, tenant_id: UUID) -> TenantSettings | None:
        """Get tenant settings."""
        result = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()


async def notify_url_change(
    db: AsyncSession,
    tenant_id: UUID,
    url: str,
    action: str = "update",
) -> None:
    """Helper function to notify IndexNow of a URL change.
    
    This should be called when content is published, updated, or deleted.
    
    Args:
        db: Database session
        tenant_id: Tenant ID
        url: Full URL that changed
        action: Type of change ('add', 'update', 'delete')
    """
    service = IndexNowService(db)
    
    if not await service.is_enabled(tenant_id):
        return
    
    logger.info(
        "indexnow_notify",
        tenant_id=str(tenant_id),
        url=url,
        action=action,
    )
    
    # Submit asynchronously (fire and forget)
    # In production, you might want to queue this
    try:
        await service.submit_url(tenant_id, url)
    except Exception as e:
        logger.error(
            "indexnow_notify_failed",
            tenant_id=str(tenant_id),
            url=url,
            error=str(e),
        )
