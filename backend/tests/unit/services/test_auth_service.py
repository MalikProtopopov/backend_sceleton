"""Unit tests for authentication service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
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
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

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

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(InvalidTokenError, match="User not found"):
            await auth_service.refresh_tokens(refresh_token)


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
