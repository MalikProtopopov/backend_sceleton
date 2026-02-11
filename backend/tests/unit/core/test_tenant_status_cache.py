"""Unit tests for TenantStatusCache and RateLimiter."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.redis import RateLimiter, TenantStatusCache


class TestTenantStatusCache:
    """Tests for TenantStatusCache Redis operations."""

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def cache(self, mock_redis: AsyncMock) -> TenantStatusCache:
        return TenantStatusCache(mock_redis)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_tenant_active_returns_true(
        self, cache: TenantStatusCache, mock_redis: AsyncMock,
    ) -> None:
        """Cached '1' should return True."""
        mock_redis.get.return_value = "1"
        result = await cache.is_tenant_active("tenant-123")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_tenant_active_returns_false(
        self, cache: TenantStatusCache, mock_redis: AsyncMock,
    ) -> None:
        """Cached '0' should return False."""
        mock_redis.get.return_value = "0"
        result = await cache.is_tenant_active("tenant-123")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_tenant_active_cache_miss(
        self, cache: TenantStatusCache, mock_redis: AsyncMock,
    ) -> None:
        """No cache entry should return None."""
        mock_redis.get.return_value = None
        result = await cache.is_tenant_active("tenant-123")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_status_active(
        self, cache: TenantStatusCache, mock_redis: AsyncMock,
    ) -> None:
        """set_status(True) should store '1' with 30s TTL."""
        await cache.set_status("tenant-123", True)
        mock_redis.setex.assert_called_once_with("tenant_status:tenant-123", 30, "1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_status_inactive(
        self, cache: TenantStatusCache, mock_redis: AsyncMock,
    ) -> None:
        """set_status(False) should store '0' with 30s TTL."""
        await cache.set_status("tenant-123", False)
        mock_redis.setex.assert_called_once_with("tenant_status:tenant-123", 30, "0")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalidate(
        self, cache: TenantStatusCache, mock_redis: AsyncMock,
    ) -> None:
        """invalidate should delete the key."""
        await cache.invalidate("tenant-123")
        mock_redis.delete.assert_called_once_with("tenant_status:tenant-123")


class TestRateLimiter:
    """Tests for RateLimiter Redis operations."""

    @pytest.fixture
    def mock_redis(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def limiter(self, mock_redis: AsyncMock) -> RateLimiter:
        return RateLimiter(mock_redis)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(
        self, limiter: RateLimiter, mock_redis: AsyncMock,
    ) -> None:
        """Request under limit should return (True, remaining, ttl)."""
        mock_redis.incr.return_value = 3
        mock_redis.ttl.return_value = 55

        allowed, remaining, ttl = await limiter.is_allowed("ip:127.0.0.1", 10, 60)

        assert allowed is True
        assert remaining == 7
        assert ttl == 55

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_allowed_at_limit(
        self, limiter: RateLimiter, mock_redis: AsyncMock,
    ) -> None:
        """Request at limit should return (True, 0, ttl)."""
        mock_redis.incr.return_value = 10
        mock_redis.ttl.return_value = 30

        allowed, remaining, ttl = await limiter.is_allowed("ip:127.0.0.1", 10, 60)

        assert allowed is True
        assert remaining == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_allowed_over_limit(
        self, limiter: RateLimiter, mock_redis: AsyncMock,
    ) -> None:
        """Request over limit should return (False, 0, ttl)."""
        mock_redis.incr.return_value = 11
        mock_redis.ttl.return_value = 45

        allowed, remaining, ttl = await limiter.is_allowed("ip:127.0.0.1", 10, 60)

        assert allowed is False
        assert remaining == 0
        assert ttl == 45

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_first_request_sets_expiry(
        self, limiter: RateLimiter, mock_redis: AsyncMock,
    ) -> None:
        """First request (incr returns 1) should set expiry."""
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = 60

        await limiter.is_allowed("ip:127.0.0.1", 10, 60)

        mock_redis.expire.assert_called_once_with("rl:ip:127.0.0.1", 60)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reset_clears_key(
        self, limiter: RateLimiter, mock_redis: AsyncMock,
    ) -> None:
        """reset should delete the rate limit key."""
        await limiter.reset("ip:127.0.0.1")
        mock_redis.delete.assert_called_once_with("rl:ip:127.0.0.1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_remaining_no_requests(
        self, limiter: RateLimiter, mock_redis: AsyncMock,
    ) -> None:
        """No requests yet should return max_requests."""
        mock_redis.get.return_value = None
        remaining = await limiter.get_remaining("ip:127.0.0.1", 10)
        assert remaining == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_remaining_some_requests(
        self, limiter: RateLimiter, mock_redis: AsyncMock,
    ) -> None:
        """Some requests should return correct remaining."""
        mock_redis.get.return_value = "7"
        remaining = await limiter.get_remaining("ip:127.0.0.1", 10)
        assert remaining == 3
