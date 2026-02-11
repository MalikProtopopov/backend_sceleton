"""Unit tests for core security module: auth, tenant checks, RBAC."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthenticationError,
    InsufficientRoleError,
    InvalidTokenError,
    PermissionDeniedError,
    TenantInactiveError,
    TokenExpiredError,
)
from app.core.security import (
    PermissionChecker,
    PlatformOwnerChecker,
    RoleChecker,
    TokenPayload,
    _check_tenant_active,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_password_reset_token,
    get_current_token,
)

# ============================================================================
# _check_tenant_active
# ============================================================================


class TestCheckTenantActive:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hit_active_returns(self):
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = True
        mock_db = AsyncMock(spec=AsyncSession)
        tid = uuid4()
        with patch("app.core.redis.get_tenant_status_cache", new_callable=AsyncMock, return_value=mock_cache):
            await _check_tenant_active(tid, mock_db)
        mock_cache.is_tenant_active.assert_called_once_with(str(tid))
        mock_db.execute.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hit_inactive_raises(self):
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = False
        mock_db = AsyncMock(spec=AsyncSession)
        with patch("app.core.redis.get_tenant_status_cache", new_callable=AsyncMock, return_value=mock_cache):
            with pytest.raises(TenantInactiveError):
                await _check_tenant_active(uuid4(), mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_db_active(self):
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = None
        mock_db = AsyncMock(spec=AsyncSession)
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = True
        mock_db.execute.return_value = result_mock
        tid = uuid4()
        with patch("app.core.redis.get_tenant_status_cache", new_callable=AsyncMock, return_value=mock_cache):
            await _check_tenant_active(tid, mock_db)
        mock_cache.set_status.assert_called_once_with(str(tid), True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_db_inactive_raises(self):
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = None
        mock_db = AsyncMock(spec=AsyncSession)
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = False
        mock_db.execute.return_value = result_mock
        with patch("app.core.redis.get_tenant_status_cache", new_callable=AsyncMock, return_value=mock_cache):
            with pytest.raises(TenantInactiveError):
                await _check_tenant_active(uuid4(), mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_miss_db_deleted_tenant_raises(self):
        mock_cache = AsyncMock()
        mock_cache.is_tenant_active.return_value = None
        mock_db = AsyncMock(spec=AsyncSession)
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock
        with patch("app.core.redis.get_tenant_status_cache", new_callable=AsyncMock, return_value=mock_cache):
            with pytest.raises(TenantInactiveError):
                await _check_tenant_active(uuid4(), mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_cache_available_queries_db(self):
        mock_db = AsyncMock(spec=AsyncSession)
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = True
        mock_db.execute.return_value = result_mock
        with patch("app.core.redis.get_tenant_status_cache", new_callable=AsyncMock, return_value=None):
            await _check_tenant_active(uuid4(), mock_db)
        mock_db.execute.assert_called_once()


# ============================================================================
# get_current_token
# ============================================================================


class TestGetCurrentToken:

    def _make_credentials(self, token_str: str) -> HTTPAuthorizationCredentials:
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_str)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_valid_access_token(self):
        token = create_access_token(
            {"sub": str(uuid4()), "tenant_id": str(uuid4()), "email": "a@b.com",
             "permissions": [], "is_superuser": False},
            expires_delta=timedelta(hours=1),
        )
        creds = self._make_credentials(token)
        with patch("app.core.redis.get_token_blacklist", new_callable=AsyncMock, return_value=None):
            payload = await get_current_token(credentials=creds)
        assert isinstance(payload, TokenPayload)
        assert payload.email == "a@b.com"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_expired_token_raises(self):
        token = create_access_token(
            {"sub": str(uuid4()), "tenant_id": str(uuid4()), "email": "a@b.com",
             "permissions": [], "is_superuser": False},
            expires_delta=timedelta(seconds=-1),
        )
        creds = self._make_credentials(token)
        with pytest.raises(TokenExpiredError):
            await get_current_token(credentials=creds)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_token_as_access_raises(self):
        token = create_refresh_token(
            {"sub": str(uuid4()), "tenant_id": str(uuid4()), "email": "a@b.com",
             "permissions": [], "is_superuser": False},
        )
        creds = self._make_credentials(token)
        with pytest.raises(InvalidTokenError):
            await get_current_token(credentials=creds)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_credentials_raises(self):
        with pytest.raises(AuthenticationError):
            await get_current_token(credentials=None)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_blacklisted_token_raises(self):
        token = create_access_token(
            {"sub": str(uuid4()), "tenant_id": str(uuid4()), "email": "a@b.com",
             "permissions": [], "is_superuser": False},
            expires_delta=timedelta(hours=1),
        )
        mock_blacklist = AsyncMock()
        mock_blacklist.is_blacklisted.return_value = True
        creds = self._make_credentials(token)
        with patch("app.core.redis.get_token_blacklist", new_callable=AsyncMock, return_value=mock_blacklist):
            with pytest.raises(InvalidTokenError):
                await get_current_token(credentials=creds)


# ============================================================================
# PermissionChecker
# ============================================================================


class TestPermissionChecker:

    def _make_user(self, is_superuser=False, permissions=None):
        user = Mock()
        user.is_superuser = is_superuser
        user.is_active = True
        if permissions is not None:
            rp_mocks = []
            for code in permissions:
                rp = Mock()
                rp.permission = Mock()
                rp.permission.code = code
                rp_mocks.append(rp)
            user.role = Mock()
            user.role.role_permissions = rp_mocks
        else:
            user.role = None
        return user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_superuser_bypass(self):
        checker = PermissionChecker("articles:create")
        user = self._make_user(is_superuser=True)
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exact_permission_match(self):
        checker = PermissionChecker("articles:create")
        user = self._make_user(permissions=["articles:create", "articles:read"])
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_wildcard_resource_match(self):
        checker = PermissionChecker("articles:delete")
        user = self._make_user(permissions=["articles:*"])
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_global_wildcard_match(self):
        checker = PermissionChecker("cases:publish")
        user = self._make_user(permissions=["*"])
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_permission_raises(self):
        checker = PermissionChecker("articles:delete")
        user = self._make_user(permissions=["articles:read"])
        with pytest.raises(PermissionDeniedError) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["restriction_level"] == "user"
        assert exc_info.value.detail["required_permission"] == "articles:delete"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_role_raises(self):
        checker = PermissionChecker("articles:read")
        user = self._make_user(permissions=None)
        with pytest.raises(PermissionDeniedError):
            await checker(user=user)


# ============================================================================
# PlatformOwnerChecker
# ============================================================================


class TestPlatformOwnerChecker:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_superuser_bypass(self):
        checker = PlatformOwnerChecker()
        user = Mock(is_superuser=True, is_active=True)
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_platform_owner_role_passes(self):
        checker = PlatformOwnerChecker()
        user = Mock(is_superuser=False, is_active=True)
        role = Mock()
        role.name = "platform_owner"
        user.role = role
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_other_role_raises(self):
        checker = PlatformOwnerChecker()
        user = Mock(is_superuser=False, is_active=True)
        role = Mock()
        role.name = "site_owner"
        user.role = role
        with pytest.raises(PermissionDeniedError):
            await checker(user=user)


# ============================================================================
# RoleChecker
# ============================================================================


class TestRoleChecker:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_superuser_bypass(self):
        checker = RoleChecker("admin")
        user = Mock(is_superuser=True, is_active=True)
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_matching_role_passes(self):
        checker = RoleChecker("editor")
        user = Mock(is_superuser=False, is_active=True)
        role = Mock()
        role.name = "editor"
        user.role = role
        result = await checker(user=user)
        assert result is user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_matching_role_raises(self):
        checker = RoleChecker("admin")
        user = Mock(is_superuser=False, is_active=True)
        role = Mock()
        role.name = "editor"
        user.role = role
        with pytest.raises(InsufficientRoleError) as exc_info:
            await checker(user=user)
        assert exc_info.value.detail["restriction_level"] == "user"
        assert exc_info.value.detail["required_role"] == "admin"


# ============================================================================
# Password Reset Tokens
# ============================================================================


class TestPasswordResetTokens:

    @pytest.mark.unit
    def test_create_token_has_correct_claims(self):
        uid = str(uuid4())
        tid = str(uuid4())
        token = create_password_reset_token(uid, tid, "a@b.com")
        from jose import jwt

        from app.config import settings
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == uid
        assert payload["tenant_id"] == tid
        assert payload["email"] == "a@b.com"
        assert payload["type"] == "password_reset"

    @pytest.mark.unit
    def test_decode_valid_token(self):
        uid = str(uuid4())
        tid = str(uuid4())
        token = create_password_reset_token(uid, tid, "a@b.com")
        payload = decode_password_reset_token(token)
        assert payload["sub"] == uid
        assert payload["type"] == "password_reset"

    @pytest.mark.unit
    def test_decode_wrong_type_raises(self):
        token = create_access_token(
            {"sub": str(uuid4()), "tenant_id": str(uuid4()), "email": "a@b.com",
             "permissions": [], "is_superuser": False},
        )
        with pytest.raises(InvalidTokenError):
            decode_password_reset_token(token)
