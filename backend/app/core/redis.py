"""Redis client wrapper for caching and rate limiting."""

from collections.abc import AsyncGenerator

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Re-exports from core.cache for backward compatibility
from app.core.cache import (  # noqa: E402, F401
    CacheClient,
    CORSOriginsCache,
    DomainTenantCache,
    TenantStatusCache,
    get_cors_origins_cache,
)

# Global Redis connection pool
_redis_pool: redis.ConnectionPool | None = None
_redis_client: Redis | None = None


async def init_redis() -> Redis:
    """Initialize Redis connection pool.

    Call this during application startup.
    """
    global _redis_pool, _redis_client

    if _redis_client is not None:
        return _redis_client

    _redis_pool = redis.ConnectionPool.from_url(
        str(settings.redis_url),
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
    )
    _redis_client = Redis(connection_pool=_redis_pool)

    try:
        await _redis_client.ping()
        logger.info("redis_connected", url=str(settings.redis_url).split("@")[-1])
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    return _redis_client


async def close_redis() -> None:
    """Close Redis connections.

    Call this during application shutdown.
    """
    global _redis_pool, _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None

    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None

    logger.info("redis_disconnected")


async def get_redis() -> AsyncGenerator[Redis, None]:
    """FastAPI dependency for Redis client."""
    if _redis_client is None:
        await init_redis()

    yield _redis_client  # type: ignore


def get_redis_client() -> Redis | None:
    """Get Redis client directly (for middleware use).

    Returns None if Redis is not initialized.
    """
    return _redis_client


async def check_redis_connection() -> bool:
    """Check Redis connectivity for health checks."""
    if _redis_client is None:
        return False

    try:
        await _redis_client.ping()
        return True
    except Exception:
        return False


class RateLimiter:
    """Rate limiter using Redis sliding window algorithm."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """Check if request is allowed under rate limit.

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_seconds)
        """
        full_key = f"rl:{key}"
        current = await self.redis.incr(full_key)
        if current == 1:
            await self.redis.expire(full_key, window_seconds)

        ttl = await self.redis.ttl(full_key)
        if ttl < 0:
            ttl = window_seconds

        remaining = max(0, max_requests - current)
        is_allowed = current <= max_requests

        return is_allowed, remaining, ttl

    async def get_remaining(self, key: str, max_requests: int) -> int:
        """Get remaining requests for a key."""
        full_key = f"rl:{key}"
        current = await self.redis.get(full_key)
        if current is None:
            return max_requests
        return max(0, max_requests - int(current))

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        full_key = f"rl:{key}"
        await self.redis.delete(full_key)


# ============================================================================
# Token Blacklist (for JWT invalidation on logout)
# ============================================================================


class TokenBlacklist:
    """Token blacklist for JWT invalidation.

    Stores blacklisted JWT token IDs (jti) with TTL matching token expiry.
    """

    PREFIX = "bl:"

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def add(self, jti: str, expires_in: int) -> None:
        key = f"{self.PREFIX}{jti}"
        await self.redis.setex(key, expires_in, "1")

    async def is_blacklisted(self, jti: str) -> bool:
        key = f"{self.PREFIX}{jti}"
        result = await self.redis.exists(key)
        return result > 0

    async def remove(self, jti: str) -> None:
        key = f"{self.PREFIX}{jti}"
        await self.redis.delete(key)


async def get_token_blacklist() -> TokenBlacklist | None:
    """Get token blacklist instance.

    Returns None if Redis is not initialized.
    """
    if _redis_client is None:
        return None
    return TokenBlacklist(_redis_client)


async def get_tenant_status_cache() -> TenantStatusCache | None:
    """Get tenant status cache instance.

    Returns None if Redis is not initialized.
    """
    if _redis_client is None:
        return None
    return TenantStatusCache(_redis_client)


async def get_domain_tenant_cache() -> DomainTenantCache | None:
    """Get domain -> tenant cache instance.

    Returns None if Redis is not initialized.
    """
    if _redis_client is None:
        return None
    return DomainTenantCache(_redis_client)
