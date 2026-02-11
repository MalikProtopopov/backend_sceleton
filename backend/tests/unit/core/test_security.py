"""Unit tests for core security module: _check_tenant_active, password reset tokens."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import InvalidTokenError, TenantInactiveError, TokenExpiredError
from app.core.security import (
    _check_tenant_active,
    create_password_reset_token,
    decode_password_reset_token,
)


class TestCheckTenantActive:
    """Tests for _check_tenant_active helper."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hit_active(self, mock_db: AsyncMock) -> None:
        """Redis cache hit returning active status should not raise."""
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = True

        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            await _check_tenant_active(uuid4(), mock_db)

        mock_cache.is_tenant_active.assert_called_once()
        mock_db.execute.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hit_inactive(self, mock_db: AsyncMock) -> None:
        """Redis cache hit returning inactive should raise TenantInactiveError."""
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = False

        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            with pytest.raises(TenantInactiveError):
                await _check_tenant_active(uuid4(), mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_db_active(self, mock_db: AsyncMock) -> None:
        """Cache miss should query DB; active tenant should set cache."""
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = None  # Cache miss

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = True
        mock_db.execute.return_value = mock_result

        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            await _check_tenant_active(uuid4(), mock_db)

        mock_db.execute.assert_called_once()
        mock_cache.set_status.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_db_inactive(self, mock_db: AsyncMock) -> None:
        """Cache miss + DB returns inactive should raise TenantInactiveError."""
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = False
        mock_db.execute.return_value = mock_result

        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            with pytest.raises(TenantInactiveError):
                await _check_tenant_active(uuid4(), mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_db_tenant_not_found(self, mock_db: AsyncMock) -> None:
        """Cache miss + tenant not in DB should raise TenantInactiveError."""
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            with pytest.raises(TenantInactiveError):
                await _check_tenant_active(uuid4(), mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_back_to_db(self, mock_db: AsyncMock) -> None:
        """When Redis is unavailable (cache=None), should fall back to DB."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = True
        mock_db.execute.return_value = mock_result

        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await _check_tenant_active(uuid4(), mock_db)

        mock_db.execute.assert_called_once()


class TestPasswordResetTokens:
    """Tests for create_password_reset_token / decode_password_reset_token."""

    @pytest.mark.unit
    def test_roundtrip(self) -> None:
        """Token should encode and decode correctly."""
        user_id = str(uuid4())
        tenant_id = str(uuid4())
        email = "test@example.com"

        token = create_password_reset_token(user_id, tenant_id, email)
        payload = decode_password_reset_token(token)

        assert payload["sub"] == user_id
        assert payload["tenant_id"] == tenant_id
        assert payload["email"] == email
        assert payload["type"] == "password_reset"

    @pytest.mark.unit
    def test_expired_token(self) -> None:
        """Expired reset token should raise TokenExpiredError."""
        from freezegun import freeze_time

        with freeze_time("2026-01-01 12:00:00"):
            token = create_password_reset_token(
                str(uuid4()), str(uuid4()), "test@example.com",
            )

        # 2 hours later (token expires in 1 hour)
        with freeze_time("2026-01-01 14:00:00"):
            with pytest.raises(TokenExpiredError):
                decode_password_reset_token(token)

    @pytest.mark.unit
    def test_wrong_token_type_raises(self) -> None:
        """Using an access token as a reset token should raise InvalidTokenError."""
        from app.core.security import create_access_token

        access_token = create_access_token({
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "test@example.com",
        })

        with pytest.raises(InvalidTokenError, match="Invalid token type"):
            decode_password_reset_token(access_token)
