"""Unit tests for RoleService — CRUD with audit logs."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Role
from app.modules.auth.service import RoleService


class TestRoleServiceAudit:
    """Tests for RoleService audit log creation."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock(spec=AsyncSession)
        db.add = Mock()
        return db

    @pytest.fixture
    def role_service(self, mock_db: AsyncMock) -> RoleService:
        svc = RoleService(mock_db, actor_id=uuid4())
        svc._audit = AsyncMock()
        return svc

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_role_creates_audit_log(
        self, role_service: RoleService, mock_db: AsyncMock,
    ) -> None:
        """Creating a role should create an audit log."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        tenant_id = uuid4()

        await role_service.create_role(
            tenant_id=tenant_id,
            name="custom_role",
            description="A custom role",
            permission_ids=[],
        )

        role_service._audit.log.assert_called_once()
        call_kwargs = role_service._audit.log.call_args.kwargs
        assert call_kwargs["action"] == "create"
        assert call_kwargs["resource_type"] == "role"
        assert call_kwargs["changes"]["name"] == "custom_role"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_role_creates_audit_log(
        self, role_service: RoleService, mock_db: AsyncMock,
    ) -> None:
        """Deleting a role should create an audit log."""
        role_id = uuid4()
        tenant_id = uuid4()
        role = Role(
            id=role_id, tenant_id=tenant_id, name="deleteable",
            description="To delete", is_system=False,
        )
        role.role_permissions = []

        get_result = Mock()
        get_result.scalar_one_or_none.return_value = role
        count_result = Mock()
        count_result.scalar.return_value = 0

        mock_db.execute.side_effect = [get_result, count_result]

        await role_service.delete_role(role_id, tenant_id)

        role_service._audit.log.assert_called_once()
        call_kwargs = role_service._audit.log.call_args.kwargs
        assert call_kwargs["action"] == "delete"
        assert call_kwargs["resource_type"] == "role"
