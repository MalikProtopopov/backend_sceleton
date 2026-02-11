"""Unit tests for Redis utilities: RateLimiter, TokenBlacklist, TenantStatusCache."""

from unittest.mock import AsyncMock

import pytest

from app.core.redis import RateLimiter, TenantStatusCache, TokenBlacklist


class TestRateLimiter:

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def limiter(self, mock_redis):
        return RateLimiter(mock_redis)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_first_request_allowed(self, limiter, mock_redis):
        mock_redis.incr.return_value = 1
        mock_redis.ttl.return_value = 60
        allowed, remaining, ttl = await limiter.is_allowed("ip:1.2.3.4", 10, 60)
        assert allowed is True
        assert remaining == 9
        mock_redis.expire.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_within_limit_allowed(self, limiter, mock_redis):
        mock_redis.incr.return_value = 5
        mock_redis.ttl.return_value = 45
        allowed, remaining, ttl = await limiter.is_allowed("ip:1.2.3.4", 10, 60)
        assert allowed is True
        assert remaining == 5
        mock_redis.expire.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_at_limit_blocked(self, limiter, mock_redis):
        mock_redis.incr.return_value = 11
        mock_redis.ttl.return_value = 30
        allowed, remaining, ttl = await limiter.is_allowed("ip:1.2.3.4", 10, 60)
        assert allowed is False
        assert remaining == 0
        assert ttl == 30

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_remaining_full(self, limiter, mock_redis):
        mock_redis.get.return_value = None
        remaining = await limiter.get_remaining("ip:1.2.3.4", 10)
        assert remaining == 10

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_remaining_partial(self, limiter, mock_redis):
        mock_redis.get.return_value = "7"
        remaining = await limiter.get_remaining("ip:1.2.3.4", 10)
        assert remaining == 3

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reset_deletes_key(self, limiter, mock_redis):
        await limiter.reset("ip:1.2.3.4")
        mock_redis.delete.assert_called_once_with("rl:ip:1.2.3.4")


class TestTokenBlacklist:

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def blacklist(self, mock_redis):
        return TokenBlacklist(mock_redis)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_add_sets_key_with_ttl(self, blacklist, mock_redis):
        await blacklist.add("jti-123", 1800)
        mock_redis.setex.assert_called_once_with("bl:jti-123", 1800, "1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_blacklisted_true(self, blacklist, mock_redis):
        mock_redis.exists.return_value = 1
        assert await blacklist.is_blacklisted("jti-123") is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_blacklisted_false(self, blacklist, mock_redis):
        mock_redis.exists.return_value = 0
        assert await blacklist.is_blacklisted("jti-999") is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_remove_deletes_key(self, blacklist, mock_redis):
        await blacklist.remove("jti-123")
        mock_redis.delete.assert_called_once_with("bl:jti-123")


class TestTenantStatusCache:

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def cache(self, mock_redis):
        return TenantStatusCache(mock_redis)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_active_cached_true(self, cache, mock_redis):
        mock_redis.get.return_value = "1"
        result = await cache.is_tenant_active("tid-123")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_active_cached_false(self, cache, mock_redis):
        mock_redis.get.return_value = "0"
        result = await cache.is_tenant_active("tid-123")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_active_cache_miss(self, cache, mock_redis):
        mock_redis.get.return_value = None
        result = await cache.is_tenant_active("tid-123")
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_status_active(self, cache, mock_redis):
        await cache.set_status("tid-123", True)
        mock_redis.setex.assert_called_once_with("tenant_status:tid-123", 30, "1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_set_status_inactive(self, cache, mock_redis):
        await cache.set_status("tid-123", False)
        mock_redis.setex.assert_called_once_with("tenant_status:tid-123", 30, "0")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalidate_deletes_key(self, cache, mock_redis):
        await cache.invalidate("tid-123")
        mock_redis.delete.assert_called_once_with("tenant_status:tid-123")
