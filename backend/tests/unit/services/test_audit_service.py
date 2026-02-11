"""Unit tests for AuditService."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.audit import AuditService
from app.modules.auth.models import AuditLog


class TestAuditService:
    """Tests for AuditService.log()."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = Mock()
        return db

    @pytest.fixture
    def audit_service(self, mock_db: AsyncMock) -> AuditService:
        return AuditService(mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_log_creates_audit_entry(
        self, audit_service: AuditService, mock_db: AsyncMock,
    ) -> None:
        """log() should create an AuditLog and add it to session."""
        tenant_id = uuid4()
        user_id = uuid4()
        resource_id = uuid4()

        entry = await audit_service.log(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="user",
            resource_id=resource_id,
            action="create",
        )

        assert isinstance(entry, AuditLog)
        assert entry.tenant_id == tenant_id
        assert entry.user_id == user_id
        assert entry.resource_type == "user"
        assert entry.resource_id == resource_id
        assert entry.action == "create"
        mock_db.add.assert_called_once_with(entry)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_log_with_changes_dict(
        self, audit_service: AuditService, mock_db: AsyncMock,
    ) -> None:
        """log() should store changes dict on the entry."""
        changes = {"is_active": {"old": True, "new": False}}

        entry = await audit_service.log(
            tenant_id=uuid4(),
            user_id=uuid4(),
            resource_type="tenant",
            resource_id=uuid4(),
            action="update",
            changes=changes,
        )

        assert entry.changes == changes

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_log_without_optional_fields(
        self, audit_service: AuditService, mock_db: AsyncMock,
    ) -> None:
        """log() with no optional fields should still work."""
        entry = await audit_service.log(
            tenant_id=uuid4(),
            user_id=None,
            resource_type="auth",
            resource_id=uuid4(),
            action="login",
        )

        assert entry.user_id is None
        assert entry.changes is None
        assert entry.ip_address is None
        assert entry.user_agent is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_log_with_ip_and_user_agent(
        self, audit_service: AuditService, mock_db: AsyncMock,
    ) -> None:
        """log() should store IP and user agent."""
        entry = await audit_service.log(
            tenant_id=uuid4(),
            user_id=uuid4(),
            resource_type="auth",
            resource_id=uuid4(),
            action="login",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert entry.ip_address == "192.168.1.1"
        assert entry.user_agent == "Mozilla/5.0"
