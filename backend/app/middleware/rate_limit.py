"""Rate limiting middleware using Redis."""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.core.logging import get_logger
from app.core.redis import RateLimiter, get_redis_client

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests.
    
    Applies different rate limits based on endpoint:
    - Public API: 100 req/min per IP
    - Login endpoint: 5 req/5min per IP (brute force protection)
    - Inquiry submission: 3 req/min per IP (spam protection)
    - Admin API: No limit (authenticated users)
    
    Rate limit headers are added to all responses:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Requests remaining in window
    - X-RateLimit-Reset: Seconds until limit resets
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        # Skip rate limiting for health checks
        path = request.url.path
        if path.startswith("/health"):
            return await call_next(request)
        
        # Get Redis client
        redis_client = get_redis_client()
        if redis_client is None:
            # Redis not available, skip rate limiting
            logger.warning("rate_limit_skipped", reason="redis_unavailable")
            return await call_next(request)
        
        # Determine rate limit based on path
        limit_config = self._get_limit_config(path, request.method)
        if limit_config is None:
            # No rate limit for this path
            return await call_next(request)
        
        max_requests, window_seconds = limit_config
        
        # Build rate limit key
        client_ip = self._get_client_ip(request)
        key = self._build_key(path, client_ip)
        
        # Check rate limit
        limiter = RateLimiter(redis_client)
        is_allowed, remaining, reset_seconds = await limiter.is_allowed(
            key, max_requests, window_seconds
        )
        
        if not is_allowed:
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=path,
                limit=max_requests,
                window=window_seconds,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "type": "https://api.cms.local/errors/rate_limit_exceeded",
                    "title": "Too Many Requests",
                    "status": 429,
                    "detail": f"Rate limit exceeded. Try again in {reset_seconds} seconds.",
                    "instance": path,
                },
                headers={
                    "Content-Type": "application/problem+json",
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_seconds),
                    "Retry-After": str(reset_seconds),
                },
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_seconds)
        
        return response
    
    def _get_limit_config(
        self, path: str, method: str
    ) -> tuple[int, int] | None:
        """Get rate limit configuration for a path.
        
        Returns:
            Tuple of (max_requests, window_seconds) or None for no limit.
        """
        # Login endpoint - strict limit for brute force protection
        # More lenient in development
        if path == f"{settings.api_prefix}/auth/login" and method == "POST":
            if settings.is_development:
                # Development: 50 requests per minute
                return (50, 60)
            return (
                settings.rate_limit_login_requests,
                settings.rate_limit_login_window_seconds,
            )
        
        # Inquiry submission - spam protection
        if path == f"{settings.api_prefix}/public/inquiries" and method == "POST":
            return (
                settings.rate_limit_inquiry_requests,
                settings.rate_limit_inquiry_window_seconds,
            )
        
        # Public API endpoints
        if "/public/" in path or path.startswith(f"{settings.api_prefix}/public"):
            return (
                settings.rate_limit_requests,
                settings.rate_limit_window_seconds,
            )
        
        # Admin API - no rate limit (authenticated)
        if "/admin/" in path:
            return None
        
        # Default rate limit for other public endpoints
        if path.startswith(settings.api_prefix):
            return (
                settings.rate_limit_requests,
                settings.rate_limit_window_seconds,
            )
        
        return None
    
    def _build_key(self, path: str, client_ip: str) -> str:
        """Build rate limit key based on path and IP."""
        # Use path prefix for grouping similar endpoints
        if "/auth/login" in path:
            return f"login:{client_ip}"
        elif "/inquiries" in path:
            return f"inquiry:{client_ip}"
        elif "/public/" in path:
            return f"public:{client_ip}"
        else:
            return f"api:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded headers (when behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"


