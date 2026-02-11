"""Unit tests for AuditService."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import AuditService


class TestAuditService:

    @pytest.fixture
    def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.add = Mock()
        return db

    @pytest.fixture
    def audit_service(self, mock_db):
        return AuditService(mock_db)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_log_creates_entry(self, audit_service, mock_db):
        tid = uuid4()
        uid = uuid4()
        rid = uuid4()
        entry = await audit_service.log(
            tenant_id=tid,
            user_id=uid,
            resource_type="user",
            resource_id=rid,
            action="create",
            changes={"email": "new@test.com"},
            ip_address="127.0.0.1",
        )
        assert entry.tenant_id == tid
        assert entry.user_id == uid
        assert entry.resource_type == "user"
        assert entry.resource_id == rid
        assert entry.action == "create"
        assert entry.changes == {"email": "new@test.com"}
        assert entry.ip_address == "127.0.0.1"
        mock_db.add.assert_called_once_with(entry)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_log_without_optional_fields(self, audit_service, mock_db):
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

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_log_returns_audit_log_instance(self, audit_service):
        from app.modules.auth.models import AuditLog
        entry = await audit_service.log(
            tenant_id=uuid4(),
            user_id=uuid4(),
            resource_type="tenant",
            resource_id=uuid4(),
            action="update",
            changes={"is_active": {"old": "True", "new": "False"}},
        )
        assert isinstance(entry, AuditLog)
