"""Unit tests for TenantService — audit logs, cache invalidation, search/sort."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenants.models import Tenant, TenantSettings
from app.modules.tenants.service import TenantService


class TestTenantServiceCreate:
    """Tests for TenantService.create — audit log creation."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock(spec=AsyncSession)
        db.add = Mock()
        return db

    @pytest.fixture
    def tenant_service(self, mock_db: AsyncMock) -> TenantService:
        svc = TenantService(mock_db, actor_id=uuid4())
        svc._audit_svc = AsyncMock()
        return svc

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_tenant_creates_audit_log(
        self, tenant_service: TenantService, mock_db: AsyncMock,
    ) -> None:
        """Creating a tenant should create an audit log."""
        from app.modules.tenants.schemas import TenantCreate

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        data = TenantCreate(name="New Corp", slug="new-corp")

        await tenant_service.create(data)

        tenant_service._audit_svc.log.assert_called_once()
        call_kwargs = tenant_service._audit_svc.log.call_args.kwargs
        assert call_kwargs["action"] == "create"
        assert call_kwargs["resource_type"] == "tenant"
        assert call_kwargs["changes"]["name"] == "New Corp"


class TestTenantServiceCacheInvalidation:
    """Tests for cache invalidation on tenant update/delete."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock(spec=AsyncSession)
        db.add = Mock()
        return db

    @pytest.fixture
    def tenant_service(self, mock_db: AsyncMock) -> TenantService:
        svc = TenantService(mock_db, actor_id=uuid4())
        svc._audit_svc = AsyncMock()
        return svc

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_tenant_invalidates_cache(
        self, tenant_service: TenantService, mock_db: AsyncMock,
    ) -> None:
        """Updating is_active should call TenantStatusCache.invalidate."""
        from app.modules.tenants.schemas import TenantUpdate

        tenant_id = uuid4()
        tenant = Tenant(id=tenant_id, name="Old Name", slug="old", is_active=True, version=1)
        tenant.settings = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = tenant
        mock_db.execute.return_value = mock_result

        data = TenantUpdate(is_active=False, version=1)

        mock_cache = AsyncMock()
        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            await tenant_service.update(tenant_id, data)

        mock_cache.invalidate.assert_called_once_with(str(tenant_id))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_invalidates_cache(
        self, tenant_service: TenantService, mock_db: AsyncMock,
    ) -> None:
        """Soft deleting a tenant should call TenantStatusCache.invalidate."""
        tenant_id = uuid4()
        tenant = Tenant(id=tenant_id, name="To Delete", slug="todelete", is_active=True, version=1)
        tenant.settings = None

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = tenant
        mock_db.execute.return_value = mock_result

        mock_cache = AsyncMock()
        with patch(
            "app.core.redis.get_tenant_status_cache",
            new_callable=AsyncMock,
            return_value=mock_cache,
        ):
            await tenant_service.soft_delete(tenant_id)

        mock_cache.invalidate.assert_called_once_with(str(tenant_id))
