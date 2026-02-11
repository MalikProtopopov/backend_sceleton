"""Unit tests for authentication service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
    TenantInactiveError,
)
from app.core.security import create_refresh_token, hash_password
from app.modules.auth.models import AdminUser, Role
from app.modules.auth.schemas import LoginRequest
from app.modules.auth.service import AuthService, UserService


# Pre-computed hash for testing
CORRECT_PASSWORD = "correct_password"


class TestAuthService:
    """Tests for AuthService."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        return db

    @pytest.fixture
    def auth_service(self, mock_db: AsyncMock) -> AuthService:
        """Create AuthService with mocked dependencies."""
        return AuthService(mock_db)

    @pytest.fixture
    def sample_user(self) -> AdminUser:
        """Create sample user for testing."""
        role = Role(
            id=uuid4(),
            name="admin",
            description="Administrator",
        )
        role.permissions = []

        user = AdminUser(
            id=uuid4(),
            tenant_id=uuid4(),
            email="test@example.com",
            password_hash=hash_password(CORRECT_PASSWORD),
            first_name="Test",
            last_name="User",
            role_id=role.id,
            is_active=True,
            is_superuser=False,
        )
        user.role = role
        return user

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_success(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """Successful authentication should return user and tokens."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        login_data = LoginRequest(email="test@example.com", password=CORRECT_PASSWORD)

        user, tokens = await auth_service.authenticate(
            data=login_data,
            tenant_id=sample_user.tenant_id,
            ip_address="127.0.0.1",
        )

        assert user.email == sample_user.email
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.expires_in > 0
        mock_db.commit.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_invalid_password(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """Authentication with wrong password should raise InvalidCredentialsError."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        login_data = LoginRequest(email="test@example.com", password="wrong_password")

        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate(
                data=login_data,
                tenant_id=sample_user.tenant_id,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
    ) -> None:
        """Authentication for non-existent user should raise InvalidCredentialsError."""
        # First call: _check_tenant_active -> active
        active_result = Mock()
        active_result.scalar_one_or_none.return_value = True
        # Second call: user lookup -> not found
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [active_result, user_result]

        login_data = LoginRequest(email="nonexistent@example.com", password="any_password")

        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate(
                data=login_data,
                tenant_id=uuid4(),
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """Authentication for inactive user should raise InvalidCredentialsError."""
        sample_user.is_active = False

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        login_data = LoginRequest(email="test@example.com", password=CORRECT_PASSWORD)

        with pytest.raises(InvalidCredentialsError, match="disabled"):
            await auth_service.authenticate(
                data=login_data,
                tenant_id=sample_user.tenant_id,
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_tokens_success(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """Refresh with valid token should return new token pair."""
        refresh_token = create_refresh_token({
            "sub": str(sample_user.id),
            "tenant_id": str(sample_user.tenant_id),
            "email": sample_user.email,
        })

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        tokens = await auth_service.refresh_tokens(refresh_token)

        assert tokens.access_token is not None
        assert tokens.refresh_token is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_type(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
    ) -> None:
        """Refresh with access token should raise InvalidTokenError."""
        from app.core.security import create_access_token

        access_token = create_access_token({
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "test@example.com",
        })

        with pytest.raises(InvalidTokenError, match="Invalid token type"):
            await auth_service.refresh_tokens(access_token)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_tokens_user_not_found(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
    ) -> None:
        """Refresh for non-existent user should raise InvalidTokenError."""
        refresh_token = create_refresh_token({
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "deleted@example.com",
        })

        # First call: _check_tenant_active -> active
        active_result = Mock()
        active_result.scalar_one_or_none.return_value = True
        # Second call: user lookup -> not found
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [active_result, user_result]

        with pytest.raises(InvalidTokenError, match="User not found"):
            await auth_service.refresh_tokens(refresh_token)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_inactive_tenant(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
    ) -> None:
        """Login to inactive tenant should raise TenantInactiveError."""
        # _check_tenant_active queries DB — return inactive
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = False
        mock_db.execute.return_value = mock_result

        login_data = LoginRequest(email="test@example.com", password="any")
        with pytest.raises(TenantInactiveError):
            await auth_service.authenticate(login_data, uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_tokens_inactive_tenant(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
    ) -> None:
        """Refresh for inactive tenant should raise TenantInactiveError."""
        refresh_token = create_refresh_token({
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "user@example.com",
        })

        # _check_tenant_active -> inactive
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = False
        mock_db.execute.return_value = mock_result

        with pytest.raises(TenantInactiveError):
            await auth_service.refresh_tokens(refresh_token)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticate_creates_audit_log(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """Successful login should create an audit log entry."""
        # First execute: _check_tenant_active -> active
        active_result = Mock()
        active_result.scalar_one_or_none.return_value = True
        # Second execute: find user
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.side_effect = [active_result, user_result]

        login_data = LoginRequest(email="test@example.com", password=CORRECT_PASSWORD)

        from unittest.mock import patch
        with patch("app.core.audit.AuditService") as MockAudit:
            mock_audit_inst = AsyncMock()
            MockAudit.return_value = mock_audit_inst
            auth_service._audit = None

            await auth_service.authenticate(login_data, sample_user.tenant_id, "127.0.0.1")

            mock_audit_inst.log.assert_called_once()
            call_kwargs = mock_audit_inst.log.call_args.kwargs
            assert call_kwargs["action"] == "login"
            assert call_kwargs["resource_type"] == "auth"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_request_password_reset_existing_user(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """Password reset for existing user should return token and send email."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        from unittest.mock import patch
        with patch("app.modules.notifications.service.EmailService") as MockEmail:
            mock_email_inst = AsyncMock()
            MockEmail.return_value = mock_email_inst

            token = await auth_service.request_password_reset(
                sample_user.email, sample_user.tenant_id,
            )

        assert token is not None
        mock_email_inst.send_password_reset_email.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_request_password_reset_nonexistent_user(
        self,
        auth_service: AuthService,
        mock_db: AsyncMock,
    ) -> None:
        """Password reset for nonexistent user should return None (no error)."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        token = await auth_service.request_password_reset("nobody@example.com", uuid4())

        assert token is None


class TestUserService:
    """Tests for UserService - read-only operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        return db

    @pytest.fixture
    def user_service(self, mock_db: AsyncMock) -> UserService:
        """Create UserService with mocked dependencies."""
        return UserService(mock_db)

    @pytest.fixture
    def sample_user(self) -> AdminUser:
        """Create sample user for testing."""
        return AdminUser(
            id=uuid4(),
            tenant_id=uuid4(),
            email="test@example.com",
            password_hash=hash_password("test_password"),
            first_name="Test",
            last_name="User",
            is_active=True,
            version=1,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        user_service: UserService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """Get by ID should return user when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        user = await user_service.get_by_id(sample_user.id, sample_user.tenant_id)

        assert user.id == sample_user.id
        assert user.email == sample_user.email

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        user_service: UserService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when user doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await user_service.get_by_id(uuid4(), uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_users_pagination(
        self,
        user_service: UserService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """List users should return paginated results."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_user]

        mock_db.execute.side_effect = [count_result, list_result]

        users, total = await user_service.list_users(sample_user.tenant_id)

        assert len(users) == 1
        assert total == 1
        assert users[0].email == sample_user.email

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_users_with_filter(
        self,
        user_service: UserService,
        mock_db: AsyncMock,
        sample_user: AdminUser,
    ) -> None:
        """List users should filter by is_active."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_user]

        mock_db.execute.side_effect = [count_result, list_result]

        users, total = await user_service.list_users(
            sample_user.tenant_id, is_active=True
        )

        assert len(users) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_users_empty(
        self,
        user_service: UserService,
        mock_db: AsyncMock,
    ) -> None:
        """List users should return empty list when no users."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        users, total = await user_service.list_users(uuid4())

        assert users == []
        assert total == 0
