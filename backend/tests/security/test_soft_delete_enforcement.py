"""Security tests for soft-delete enforcement (SEC-11 to SEC-13).

Verifies that soft-deleted users and tenants cannot be accessed.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.security
class TestSoftDeletedUserAccess:
    """SEC-11: Deleted user cannot login."""

    @pytest.mark.asyncio
    async def test_deleted_user_cannot_login(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        deleted_user: AdminUser,
    ) -> None:
        """Soft-deleted user should not be able to authenticate."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": deleted_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        # Should fail because user query filters deleted_at IS NULL
        assert response.status_code == 401
        assert "invalid_credentials" in response.json()["detail"]["type"]


@pytest.mark.security
class TestSoftDeletedTenantAccess:
    """SEC-12, SEC-13: Deleted tenant not served by public API or tenant list."""

    @pytest.mark.asyncio
    async def test_deleted_tenant_not_in_public_api(
        self,
        client: AsyncClient,
        deleted_tenant: Tenant,
    ) -> None:
        """SEC-12: Public API for deleted tenant should return 404."""
        response = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(deleted_tenant.id)},
        )
        assert response.status_code in (400, 404)

    @pytest.mark.asyncio
    async def test_deleted_tenant_not_in_tenant_list(
        self,
        platform_owner_client: AsyncClient,
        deleted_tenant: Tenant,
    ) -> None:
        """SEC-13: Deleted tenant should not appear in tenant list."""
        response = await platform_owner_client.get("/api/v1/tenants")
        assert response.status_code == 200
        items = response.json()["items"]
        tenant_ids = [t["id"] for t in items]
        assert str(deleted_tenant.id) not in tenant_ids
