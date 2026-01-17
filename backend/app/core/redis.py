"""Redis client wrapper for caching and rate limiting."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    
    # Test connection
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
    """FastAPI dependency for Redis client.
    
    Usage:
        @router.get("/items")
        async def get_items(redis: Redis = Depends(get_redis)):
            value = await redis.get("key")
    """
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
    """Rate limiter using Redis sliding window algorithm.
    
    Usage:
        limiter = RateLimiter(redis_client)
        allowed = await limiter.is_allowed("user:123", max_requests=100, window_seconds=60)
        if not allowed:
            raise HTTPException(429, "Rate limit exceeded")
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (e.g., "ip:192.168.1.1" or "user:uuid")
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_seconds)
        """
        full_key = f"rl:{key}"
        
        # Increment counter
        current = await self.redis.incr(full_key)
        
        # Set expiry on first request
        if current == 1:
            await self.redis.expire(full_key, window_seconds)
        
        # Get TTL for reset time
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
    Used to invalidate tokens on logout before they naturally expire.
    
    Usage:
        blacklist = TokenBlacklist(redis_client)
        
        # On logout
        await blacklist.add(jti="token-uuid", expires_in=1800)
        
        # On token validation
        if await blacklist.is_blacklisted(jti="token-uuid"):
            raise InvalidTokenError("Token has been revoked")
    """
    
    PREFIX = "bl:"  # Blacklist prefix
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def add(self, jti: str, expires_in: int) -> None:
        """Add a token to the blacklist.
        
        Args:
            jti: JWT token ID (unique identifier)
            expires_in: TTL in seconds (should match token's remaining lifetime)
        """
        key = f"{self.PREFIX}{jti}"
        await self.redis.setex(key, expires_in, "1")
    
    async def is_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted.
        
        Args:
            jti: JWT token ID to check
            
        Returns:
            True if token is blacklisted, False otherwise
        """
        key = f"{self.PREFIX}{jti}"
        result = await self.redis.exists(key)
        return result > 0
    
    async def remove(self, jti: str) -> None:
        """Remove a token from the blacklist (rarely needed).
        
        Args:
            jti: JWT token ID to remove
        """
        key = f"{self.PREFIX}{jti}"
        await self.redis.delete(key)


async def get_token_blacklist() -> TokenBlacklist | None:
    """Get token blacklist instance.
    
    Returns None if Redis is not initialized.
    """
    if _redis_client is None:
        return None
    return TokenBlacklist(_redis_client)


class CacheClient:
    """Simple cache client wrapper for Redis.
    
    Usage:
        cache = CacheClient(redis_client)
        
        # Get or set
        data = await cache.get("services:tenant:locale")
        if data is None:
            data = await fetch_services()
            await cache.set("services:tenant:locale", data, ttl=300)
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        return await self.redis.get(f"cache:{key}")
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: int = 300,
    ) -> None:
        """Set value in cache with TTL."""
        await self.redis.setex(f"cache:{key}", ttl, value)
    
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        await self.redis.delete(f"cache:{key}")
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.
        
        Args:
            pattern: Glob pattern (e.g., "services:tenant123:*")
            
        Returns:
            Number of keys deleted
        """
        full_pattern = f"cache:{pattern}"
        keys = []
        
        async for key in self.redis.scan_iter(match=full_pattern):
            keys.append(key)
        
        if keys:
            return await self.redis.delete(*keys)
        
        return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self.redis.exists(f"cache:{key}") > 0
    
    async def ttl(self, key: str) -> int:
        """Get remaining TTL for a key."""
        return await self.redis.ttl(f"cache:{key}")


