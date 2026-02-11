"""Integration tests for cross-tenant user management (Phase 3).

T3-01 to T3-10: platform_owner cross-tenant access, site_owner/editor denial,
default tenant scoping, tenant search/sort, users_count.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant


@pytest.mark.integration
class TestCrossTenantPlatformOwner:
    """T3-01, T3-02, T3-05, T3-06: Platform owner cross-tenant operations."""

    @pytest.mark.asyncio
    async def test_platform_owner_lists_users_of_another_tenant(
        self,
        platform_owner_client: AsyncClient,
        tenant_b: Tenant,
        tenant_b_user: AdminUser,
    ) -> None:
        """Platform owner should list users of tenant_b via tenant_id param."""
        response = await platform_owner_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        emails = [u["email"] for u in data["items"]]
        assert tenant_b_user.email in emails

    @pytest.mark.asyncio
    async def test_platform_owner_creates_user_in_another_tenant(
        self,
        platform_owner_client: AsyncClient,
        tenant_b: Tenant,
        tenant_b_role,
        mock_email_service,
    ) -> None:
        """Platform owner should create user in tenant_b."""
        response = await platform_owner_client.post(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
            json={
                "email": f"new-cross-{uuid4().hex[:8]}@example.com",
                "first_name": "Cross",
                "last_name": "Tenant",
                "password": "securepassword123",
                "role_id": str(tenant_b_role.id),
                "send_credentials": False,
            },
        )
        assert response.status_code == 201
        assert response.json()["tenant_id"] == str(tenant_b.id)

    @pytest.mark.asyncio
    async def test_platform_owner_updates_user_in_another_tenant(
        self,
        platform_owner_client: AsyncClient,
        tenant_b: Tenant,
        tenant_b_user: AdminUser,
    ) -> None:
        """Platform owner should update user in tenant_b."""
        response = await platform_owner_client.patch(
            f"/api/v1/auth/users/{tenant_b_user.id}",
            params={"tenant_id": str(tenant_b.id)},
            json={"first_name": "Updated", "version": 1},
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Updated"


@pytest.mark.integration
class TestCrossTenantDenied:
    """T3-03, T3-04: Non-privileged users cannot cross-tenant."""

    @pytest.mark.asyncio
    async def test_site_owner_cannot_list_users_of_another_tenant(
        self,
        site_owner_client: AsyncClient,
        tenant_b: Tenant,
    ) -> None:
        """site_owner should get 403 when trying to access tenant_b users."""
        response = await site_owner_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert response.status_code == 403
        assert "permission_denied" in response.json()["detail"]["type"]

    @pytest.mark.asyncio
    async def test_editor_cannot_use_tenant_id_param(
        self,
        editor_client: AsyncClient,
        tenant_b: Tenant,
    ) -> None:
        """editor should get 403 when using tenant_id param."""
        response = await editor_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestDefaultTenantScoping:
    """T3-07: Omitting tenant_id defaults to own tenant."""

    @pytest.mark.asyncio
    async def test_platform_owner_defaults_to_own_tenant(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        platform_owner_user: AdminUser,
    ) -> None:
        """Without tenant_id param, platform_owner sees own tenant users."""
        response = await platform_owner_client.get("/api/v1/auth/users")
        assert response.status_code == 200
        data = response.json()
        # All returned users should be from test_tenant
        for user in data["items"]:
            assert user["tenant_id"] == str(test_tenant.id)


@pytest.mark.integration
class TestTenantSearchSort:
    """T3-08, T3-09, T3-10: Tenant list search/sort/users_count."""

    @pytest.mark.asyncio
    async def test_tenant_search_by_name(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """Search by tenant name should filter results."""
        response = await platform_owner_client.get(
            "/api/v1/tenants",
            params={"search": "Tenant B"},
        )
        assert response.status_code == 200
        items = response.json()["items"]
        names = [t["name"] for t in items]
        assert "Tenant B Corp" in names

    @pytest.mark.asyncio
    async def test_tenant_sort_by_name_asc(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """Sorting by name ascending should order alphabetically."""
        response = await platform_owner_client.get(
            "/api/v1/tenants",
            params={"sort_by": "name", "sort_order": "asc"},
        )
        assert response.status_code == 200
        items = response.json()["items"]
        if len(items) >= 2:
            names = [t["name"] for t in items]
            assert names == sorted(names)
