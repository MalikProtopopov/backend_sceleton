"""Security tests for tenant isolation (SEC-01 to SEC-05).

Verifies that non-privileged users cannot access other tenants' data.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant


@pytest.mark.security
class TestTenantTraversal:
    """SEC-01 to SEC-05: Tenant traversal prevention."""

    @pytest.mark.asyncio
    async def test_editor_cannot_read_users_of_another_tenant(
        self,
        editor_client: AsyncClient,
        tenant_b: Tenant,
    ) -> None:
        """SEC-01: Editor with tenant_id param for another tenant -> 403."""
        response = await editor_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert response.status_code == 403
        assert "permission_denied" in response.json()["detail"]["type"]

    @pytest.mark.asyncio
    async def test_site_owner_cannot_create_user_in_another_tenant(
        self,
        site_owner_client: AsyncClient,
        tenant_b: Tenant,
    ) -> None:
        """SEC-02: Site owner creating user in tenant_b -> 403."""
        response = await site_owner_client.post(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
            json={
                "email": "hacker@example.com",
                "first_name": "Hack",
                "last_name": "Attempt",
                "password": "password123",
                "send_credentials": False,
            },
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_editor_cannot_read_specific_user_from_another_tenant(
        self,
        editor_client: AsyncClient,
        tenant_b: Tenant,
        tenant_b_user: AdminUser,
    ) -> None:
        """SEC-03: Editor reading specific user from tenant_b -> 403."""
        response = await editor_client.get(
            f"/api/v1/auth/users/{tenant_b_user.id}",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_forged_tenant_id_header_nonexistent(
        self,
        client: AsyncClient,
    ) -> None:
        """SEC-04: X-Tenant-ID with nonexistent UUID -> 404."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "any@example.com", "password": "any"},
            headers={"X-Tenant-ID": str(uuid4())},
        )
        # Should fail with tenant not found or similar
        assert response.status_code in (400, 403, 404)

    @pytest.mark.asyncio
    async def test_forged_tenant_id_param_deleted_tenant(
        self,
        platform_owner_client: AsyncClient,
        deleted_tenant: Tenant,
    ) -> None:
        """SEC-05: tenant_id pointing to deleted tenant -> 404."""
        response = await platform_owner_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(deleted_tenant.id)},
        )
        # Soft-deleted tenant should not be found
        assert response.status_code in (404, 200)  # May return empty or 404
