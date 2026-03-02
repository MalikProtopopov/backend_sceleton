"""Unified cache layer.

Centralizes all application caches that sit on top of Redis.
``redis.py`` stays responsible for connection management, rate limiting,
and token blacklisting.  This module owns domain-specific caches.
"""

from __future__ import annotations

import time
from urllib.parse import urlparse

from redis.asyncio import Redis

from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Facade that groups all application caches.

    Instantiate once (after Redis is initialised) and pass around,
    or use the module-level helper ``get_cache_manager()``.
    """

    def __init__(self, redis_client: Redis) -> None:
        self.tenant_status = TenantStatusCache(redis_client)
        self.domain_tenant = DomainTenantCache(redis_client)
        self.client = CacheClient(redis_client)

    async def invalidate_tenant(self, tenant_id: str) -> None:
        """Convenience: invalidate all caches related to a single tenant."""
        await self.tenant_status.invalidate(tenant_id)
        await self.domain_tenant.invalidate_tenant(tenant_id)


class TenantStatusCache:
    """Cache for tenant active/inactive status.

    Uses Redis with short TTL to avoid DB hit on every authenticated request.
    Provides explicit invalidation when tenant status changes.
    """

    PREFIX = "tenant_status:"
    TTL = 30

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def is_tenant_active(self, tenant_id: str) -> bool | None:
        """Check cached tenant active status.

        Returns True/False if cached, None if not in cache.
        """
        key = f"{self.PREFIX}{tenant_id}"
        value = await self.redis.get(key)
        if value is None:
            return None
        return value == "1"

    async def set_status(self, tenant_id: str, is_active: bool) -> None:
        """Cache tenant active status."""
        key = f"{self.PREFIX}{tenant_id}"
        await self.redis.setex(key, self.TTL, "1" if is_active else "0")

    async def invalidate(self, tenant_id: str) -> None:
        """Invalidate cached status for a tenant."""
        key = f"{self.PREFIX}{tenant_id}"
        await self.redis.delete(key)


class DomainTenantCache:
    """Cache for domain -> tenant resolution.

    Stores JSON-encoded tenant info keyed by domain name.
    Used by the public ``/public/tenants/by-domain/{domain}`` endpoint
    so the admin SPA can resolve its hostname to a tenant without
    hitting the database on every page load.
    """

    PREFIX = "domain_tenant:"
    TTL = 300

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get(self, domain: str) -> str | None:
        """Return cached JSON string for *domain*, or ``None``."""
        key = f"{self.PREFIX}{domain.lower()}"
        return await self.redis.get(key)

    async def set(self, domain: str, data_json: str) -> None:
        """Store *data_json* for *domain* with a 5-minute TTL."""
        key = f"{self.PREFIX}{domain.lower()}"
        await self.redis.setex(key, self.TTL, data_json)

    async def invalidate(self, domain: str) -> None:
        """Remove cached entry for *domain*."""
        key = f"{self.PREFIX}{domain.lower()}"
        await self.redis.delete(key)

    async def invalidate_tenant(self, tenant_id: str) -> None:
        """Remove **all** cached domains that belong to *tenant_id*.

        This uses SCAN so it's safe for production Redis.
        """
        async for key in self.redis.scan_iter(match=f"{self.PREFIX}*"):
            val = await self.redis.get(key)
            if val and tenant_id in val:
                await self.redis.delete(key)


class CORSOriginsCache:
    """In-memory cache of allowed CORS origins backed by the database.

    Combines static origins from ``CORS_ORIGINS`` env var with dynamic
    origins derived from ``tenant_domains`` and ``tenant_settings.site_url``.
    The cache auto-refreshes every ``TTL`` seconds or can be explicitly
    invalidated when domains / settings change.
    """

    TTL = 300

    def __init__(self) -> None:
        self._origins: set[str] = set()
        self._loaded_at: float = 0.0
        self._static_origins: set[str] = set()

    def set_static_origins(self, origins: list[str]) -> None:
        """Store the static fallback origins from .env (called once at startup)."""
        self._static_origins = {o.rstrip("/") for o in origins if o}

    async def get_allowed_origins(self) -> set[str]:
        """Return the full set of allowed origins (static + dynamic).

        Reloads from the database when the TTL has elapsed.
        """
        now = time.monotonic()
        if self._origins and (now - self._loaded_at) < self.TTL:
            return self._origins

        try:
            db_origins = await self._load_from_db()
        except Exception:
            logger.warning("cors_origins_load_failed", exc_info=True)
            db_origins = set()

        self._origins = self._static_origins | db_origins
        self._loaded_at = now
        logger.info(
            "cors_origins_refreshed",
            total=len(self._origins),
            static=len(self._static_origins),
            dynamic=len(db_origins),
        )
        return self._origins

    def invalidate(self) -> None:
        """Force a reload on the next ``get_allowed_origins`` call."""
        self._loaded_at = 0.0

    def is_origin_allowed(self, origin: str) -> bool:
        """Fast synchronous check against the already-loaded set."""
        return origin.rstrip("/") in self._origins

    @staticmethod
    async def _load_from_db() -> set[str]:
        from sqlalchemy import text

        from app.core.database import async_session_factory

        query = text("""
            SELECT 'https://' || td.domain AS origin
            FROM tenant_domains td
            JOIN tenants t ON t.id = td.tenant_id
            WHERE t.deleted_at IS NULL AND t.is_active = true
            UNION
            SELECT ts.site_url AS origin
            FROM tenant_settings ts
            JOIN tenants t ON t.id = ts.tenant_id
            WHERE t.deleted_at IS NULL AND t.is_active = true
              AND ts.site_url IS NOT NULL AND ts.site_url != ''
        """)

        origins: set[str] = set()
        async with async_session_factory() as session:
            result = await session.execute(query)
            for (raw_origin,) in result:
                origin = _normalize_origin(raw_origin)
                if origin:
                    origins.add(origin)
        return origins


class CacheClient:
    """Simple cache client wrapper for Redis.

    Usage:
        cache = CacheClient(redis_client)
        data = await cache.get("services:tenant:locale")
        if data is None:
            data = await fetch_services()
            await cache.set("services:tenant:locale", data, ttl=300)
    """

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get(self, key: str) -> str | None:
        return await self.redis.get(f"cache:{key}")

    async def set(self, key: str, value: str, ttl: int = 300) -> None:
        await self.redis.setex(f"cache:{key}", ttl, value)

    async def delete(self, key: str) -> None:
        await self.redis.delete(f"cache:{key}")

    async def delete_pattern(self, pattern: str) -> int:
        full_pattern = f"cache:{pattern}"
        keys = []
        async for key in self.redis.scan_iter(match=full_pattern):
            keys.append(key)
        if keys:
            return await self.redis.delete(*keys)
        return 0

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(f"cache:{key}") > 0

    async def ttl(self, key: str) -> int:
        return await self.redis.ttl(f"cache:{key}")


def _normalize_origin(url: str) -> str:
    """Extract ``scheme://host[:port]`` from a URL, stripping path/query."""
    url = url.strip().rstrip("/")
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if not parsed.scheme or not parsed.hostname:
        return ""
    origin = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port and parsed.port not in (80, 443):
        origin += f":{parsed.port}"
    return origin


_cors_origins_cache = CORSOriginsCache()


def get_cors_origins_cache() -> CORSOriginsCache:
    """Return the module-level CORS origins cache singleton."""
    return _cors_origins_cache
