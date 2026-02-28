"""Rate limiting middleware using Redis with in-memory fallback."""

import time
from collections import defaultdict
from threading import Lock
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.core.logging import get_logger
from app.core.redis import RateLimiter, get_redis_client

logger = get_logger(__name__)


class _InMemoryRateLimiter:
    """Simple in-memory rate limiter used as fallback when Redis is unavailable.

    Only applied to critical endpoints (login, inquiry) to prevent abuse
    while Redis is down.  Non-critical endpoints are allowed through.
    """

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, key: str, max_requests: int, window: int) -> tuple[bool, int, int]:
        now = time.monotonic()
        with self._lock:
            hits = self._buckets[key]
            cutoff = now - window
            hits[:] = [t for t in hits if t > cutoff]
            if len(hits) >= max_requests:
                reset = int(hits[0] + window - now) + 1
                return False, 0, reset
            hits.append(now)
            return True, max_requests - len(hits), window


_mem_limiter = _InMemoryRateLimiter()

_CRITICAL_KEYS = {"login", "inquiry"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests.
    
    Applies different rate limits based on endpoint:
    - Public API: 100 req/min per IP
    - Login endpoint: 5 req/5min per IP (brute force protection)
    - Inquiry submission: 3 req/min per IP (spam protection)
    - Admin API: No limit (authenticated users)
    
    When Redis is unavailable, an in-memory fallback protects critical
    endpoints (login, inquiry) so brute-force protection is never silently
    disabled.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        path = request.url.path
        if path.startswith("/health"):
            return await call_next(request)

        limit_config = self._get_limit_config(path, request.method)
        if limit_config is None:
            return await call_next(request)

        max_requests, window_seconds = limit_config
        client_ip = self._get_client_ip(request)
        key = self._build_key(path, client_ip)

        redis_client = get_redis_client()
        if redis_client is not None:
            limiter = RateLimiter(redis_client)
            is_allowed, remaining, reset_seconds = await limiter.is_allowed(
                key, max_requests, window_seconds
            )
        else:
            bucket_name = key.split(":")[0]
            if bucket_name in _CRITICAL_KEYS:
                is_allowed, remaining, reset_seconds = _mem_limiter.is_allowed(
                    key, max_requests, window_seconds
                )
            else:
                return await call_next(request)

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
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_seconds)
        return response
    
    def _get_limit_config(
        self, path: str, method: str
    ) -> tuple[int, int] | None:
        is_login = (
            path == f"{settings.api_prefix}/auth/login"
            or path == "/auth/login"
        ) and method == "POST"
        if is_login:
            if settings.is_development:
                return (50, 60)
            return (
                settings.rate_limit_login_requests,
                settings.rate_limit_login_window_seconds,
            )
        
        if path == f"{settings.api_prefix}/public/inquiries" and method == "POST":
            return (
                settings.rate_limit_inquiry_requests,
                settings.rate_limit_inquiry_window_seconds,
            )
        
        if "/public/" in path or path.startswith(f"{settings.api_prefix}/public"):
            return (
                settings.rate_limit_requests,
                settings.rate_limit_window_seconds,
            )
        
        if "/admin/" in path:
            return None
        
        if path.startswith(settings.api_prefix) or path.startswith("/auth"):
            return (
                settings.rate_limit_requests,
                settings.rate_limit_window_seconds,
            )
        
        return None
    
    def _build_key(self, path: str, client_ip: str) -> str:
        if "/auth/login" in path:
            return f"login:{client_ip}"
        elif "/inquiries" in path:
            return f"inquiry:{client_ip}"
        elif "/public/" in path:
            return f"public:{client_ip}"
        else:
            return f"api:{client_ip}"
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP preferring X-Real-IP set by the reverse proxy."""
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host
        
        return "unknown"


