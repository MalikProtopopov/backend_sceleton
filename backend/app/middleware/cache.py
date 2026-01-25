"""Cache headers middleware for Public API."""

import hashlib
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding Cache-Control and ETag headers to public API responses.
    
    Cache policy:
    - GET /api/v1/public/* → Cache-Control: public, max-age=300 (5 min)
    - GET /api/v1/admin/* → Cache-Control: private, no-cache
    - Other methods → No caching
    
    ETag support:
    - Generates ETag from response body hash
    - Handles If-None-Match header for conditional requests
    """
    
    # Cache durations in seconds
    PUBLIC_CACHE_MAX_AGE = 300  # 5 minutes for public endpoints
    STATIC_CACHE_MAX_AGE = 3600  # 1 hour for static content like sitemap
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        # Only cache GET requests
        if request.method != "GET":
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            return response
        
        # Skip caching for health checks and docs
        path = request.url.path
        if path.startswith("/health") or path in ("/docs", "/redoc", "/openapi.json"):
            return await call_next(request)
        
        # Check for conditional request (If-None-Match)
        if_none_match = request.headers.get("if-none-match")
        
        # Process request
        response = await call_next(request)
        
        # Don't cache error responses
        if response.status_code >= 400:
            response.headers["Cache-Control"] = "no-store"
            return response
        
        # Determine cache policy based on path
        cache_policy = self._get_cache_policy(path)
        response.headers["Cache-Control"] = cache_policy["cache_control"]
        
        # Add Vary header for proper caching with different Accept-Language
        if "public" in cache_policy["cache_control"]:
            response.headers["Vary"] = "Accept-Language, Accept-Encoding"
        
        # Generate and add ETag for public responses
        if cache_policy["add_etag"] and hasattr(response, "body"):
            try:
                # Get response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                # Generate ETag
                etag = self._generate_etag(body)
                response.headers["ETag"] = etag
                
                # Check if client has valid cached version
                if if_none_match and if_none_match == etag:
                    return Response(
                        status_code=304,
                        headers={
                            "ETag": etag,
                            "Cache-Control": cache_policy["cache_control"],
                        },
                    )
                
                # Return response with body
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception as e:
                logger.warning("etag_generation_failed", error=str(e))
        
        return response
    
    def _get_cache_policy(self, path: str) -> dict:
        """Determine cache policy based on request path."""
        # Public API endpoints - cacheable
        if "/public/" in path:
            # Tenant data - short cache (logo/name may change)
            if "/public/tenants/" in path:
                return {
                    "cache_control": "public, max-age=60",  # 1 minute
                    "add_etag": True,
                }
            # Static content like sitemap, robots - longer cache
            if "/sitemap" in path or "/robots" in path:
                return {
                    "cache_control": f"public, max-age={self.STATIC_CACHE_MAX_AGE}",
                    "add_etag": True,
                }
            # Regular public API
            return {
                "cache_control": f"public, max-age={self.PUBLIC_CACHE_MAX_AGE}",
                "add_etag": True,
            }
        
        # Admin API - private, no cache
        # Includes /admin/, /auth/, /feature-flags/, /tenants/ (non-public)
        if "/admin/" in path or "/auth/" in path or "/feature-flags" in path:
            return {
                "cache_control": "private, no-cache, no-store, must-revalidate",
                "add_etag": False,
            }
        
        # Tenants management (not public) - no cache
        if "/tenants" in path and "/public/" not in path:
            return {
                "cache_control": "private, no-cache, no-store, must-revalidate",
                "add_etag": False,
            }
        
        # Default - short cache
        return {
            "cache_control": f"public, max-age={self.PUBLIC_CACHE_MAX_AGE}",
            "add_etag": True,
        }
    
    def _generate_etag(self, body: bytes) -> str:
        """Generate ETag from response body."""
        hash_value = hashlib.md5(body).hexdigest()
        return f'"{hash_value}"'


