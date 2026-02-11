"""Unit tests for UserService — multi-tenant features (audit, email, force_password_change)."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError
from app.core.security import hash_password
from app.modules.auth.models import AdminUser, AuditLog, Role
from app.modules.auth.schemas import PasswordChange, UserCreate, UserUpdate
from app.modules.auth.service import UserService


CORRECT_PASSWORD = "correct_password"


def _make_mock_db() -> AsyncMock:
    """Create a mock DB that passes @transactional isinstance check."""
    db = AsyncMock(spec=AsyncSession)
    db.add = Mock()
    return db


class TestUserServiceCreate:
    """Tests for UserService.create — audit logs, email, force_password_change."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return _make_mock_db()

    @pytest.fixture
    def user_service(self, mock_db: AsyncMock) -> UserService:
        svc = UserService(mock_db, actor_id=uuid4())
        svc._audit = AsyncMock()
        return svc

    def _setup_create_mocks(self, mock_db: AsyncMock) -> None:
        """Set up mocks for user creation: no existing user, tenant name query."""
        existing_result = Mock()
        existing_result.scalar_one_or_none.return_value = None
        tenant_result = Mock()
        tenant_result.scalar_one_or_none.return_value = "Test Company"
        mock_db.execute.side_effect = [existing_result, tenant_result]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_user_sets_force_password_change(
        self, user_service: UserService, mock_db: AsyncMock,
    ) -> None:
        """New user should have force_password_change=True."""
        self._setup_create_mocks(mock_db)

        data = UserCreate(
            email="new@example.com",
            first_name="New",
            last_name="User",
            password="securepassword123",
            send_credentials=False,
        )

        user = await user_service.create(uuid4(), data)
        assert user.force_password_change is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_user_creates_audit_log(
        self, user_service: UserService, mock_db: AsyncMock,
    ) -> None:
        """Creating a user should create an audit log entry."""
        self._setup_create_mocks(mock_db)

        data = UserCreate(
            email="audited@example.com",
            first_name="Audited",
            last_name="User",
            password="securepassword123",
            send_credentials=False,
        )

        await user_service.create(uuid4(), data)

        user_service._audit.log.assert_called_once()
        call_kwargs = user_service._audit.log.call_args.kwargs
        assert call_kwargs["action"] == "create"
        assert call_kwargs["resource_type"] == "user"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_user_sends_welcome_email(
        self, user_service: UserService, mock_db: AsyncMock,
    ) -> None:
        """send_credentials=True should trigger send_welcome_email."""
        self._setup_create_mocks(mock_db)

        data = UserCreate(
            email="welcome@example.com",
            first_name="Welcome",
            last_name="User",
            password="securepassword123",
            send_credentials=True,
        )

        with patch("app.modules.notifications.service.EmailService") as MockEmail:
            mock_email_inst = AsyncMock()
            MockEmail.return_value = mock_email_inst
            await user_service.create(uuid4(), data)

            mock_email_inst.send_welcome_email.assert_called_once()
            call_kwargs = mock_email_inst.send_welcome_email.call_args.kwargs
            assert call_kwargs["to_email"] == "welcome@example.com"
            assert call_kwargs["first_name"] == "Welcome"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_user_no_email_when_send_credentials_false(
        self, user_service: UserService, mock_db: AsyncMock,
    ) -> None:
        """send_credentials=False should not trigger email."""
        self._setup_create_mocks(mock_db)

        data = UserCreate(
            email="nomail@example.com",
            first_name="NoMail",
            last_name="User",
            password="securepassword123",
            send_credentials=False,
        )

        with patch("app.modules.notifications.service.EmailService") as MockEmail:
            await user_service.create(uuid4(), data)
            MockEmail.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_email_failure_does_not_block_creation(
        self, user_service: UserService, mock_db: AsyncMock,
    ) -> None:
        """Email exception should be caught; user creation should succeed."""
        self._setup_create_mocks(mock_db)

        data = UserCreate(
            email="failmail@example.com",
            first_name="FailMail",
            last_name="User",
            password="securepassword123",
            send_credentials=True,
        )

        with patch("app.modules.notifications.service.EmailService") as MockEmail:
            mock_email_inst = AsyncMock()
            mock_email_inst.send_welcome_email.side_effect = Exception("SMTP error")
            MockEmail.return_value = mock_email_inst
            user = await user_service.create(uuid4(), data)

        assert user.email == "failmail@example.com"


class TestUserServiceChangePassword:
    """Tests for UserService.change_password — force_password_change, audit."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return _make_mock_db()

    @pytest.fixture
    def user_service(self, mock_db: AsyncMock) -> UserService:
        svc = UserService(mock_db, actor_id=uuid4())
        svc._audit = AsyncMock()
        return svc

    @pytest.fixture
    def sample_user(self) -> AdminUser:
        return AdminUser(
            id=uuid4(),
            tenant_id=uuid4(),
            email="test@example.com",
            password_hash=hash_password(CORRECT_PASSWORD),
            first_name="Test",
            last_name="User",
            is_active=True,
            force_password_change=True,
            version=1,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_change_password_clears_force_password_change(
        self, user_service: UserService, mock_db: AsyncMock, sample_user: AdminUser,
    ) -> None:
        """Changing password should set force_password_change=False."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        data = PasswordChange(
            current_password=CORRECT_PASSWORD,
            new_password="newsecurepassword123",
        )

        await user_service.change_password(
            sample_user.id, sample_user.tenant_id, data,
        )

        assert sample_user.force_password_change is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_change_password_creates_audit_log_no_plaintext(
        self, user_service: UserService, mock_db: AsyncMock, sample_user: AdminUser,
    ) -> None:
        """Password change audit log should use '***' not actual password."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute.return_value = mock_result

        data = PasswordChange(
            current_password=CORRECT_PASSWORD,
            new_password="newsecurepassword123",
        )

        await user_service.change_password(
            sample_user.id, sample_user.tenant_id, data,
        )

        user_service._audit.log.assert_called_once()
        changes = user_service._audit.log.call_args.kwargs["changes"]
        assert changes["password"]["old"] == "***"
        assert changes["password"]["new"] == "***"
        assert "newsecurepassword123" not in str(changes)


class TestUserServiceSoftDelete:
    """Tests for UserService.soft_delete — audit log."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return _make_mock_db()

    @pytest.fixture
    def user_service(self, mock_db: AsyncMock) -> UserService:
        svc = UserService(mock_db, actor_id=uuid4())
        svc._audit = AsyncMock()
        return svc

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_creates_audit_log(
        self, user_service: UserService, mock_db: AsyncMock,
    ) -> None:
        """Soft delete should create an audit log with action=delete."""
        user = AdminUser(
            id=uuid4(),
            tenant_id=uuid4(),
            email="todelete@example.com",
            password_hash="hash",
            first_name="Delete",
            last_name="Me",
            is_active=True,
            version=1,
        )
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_result

        await user_service.soft_delete(user.id, user.tenant_id)

        user_service._audit.log.assert_called_once()
        call_kwargs = user_service._audit.log.call_args.kwargs
        assert call_kwargs["action"] == "delete"
        assert call_kwargs["resource_type"] == "user"
