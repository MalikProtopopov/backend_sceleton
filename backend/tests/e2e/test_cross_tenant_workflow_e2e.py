"""E2E test: Cross-tenant workflow.

Scenario 3: Platform owner manages users across tenants,
verifies isolation for non-privileged users.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.e2e
class TestCrossTenantWorkflowE2E:
    """Platform owner cross-tenant management + isolation verification."""

    @pytest.mark.asyncio
    async def test_cross_tenant_management_and_isolation(
        self,
        platform_owner_client: AsyncClient,
        site_owner_client: AsyncClient,
        client: AsyncClient,
        test_tenant: Tenant,
        tenant_b: Tenant,
        tenant_b_role,
        site_owner_user: AdminUser,
        mock_email_service,
    ) -> None:
        """E2E Scenario 3: Cross-tenant management with isolation checks."""

        user_email = f"cross-e2e-{uuid4().hex[:8]}@example.com"

        # Step 1: Platform owner creates user in tenant_b
        create_resp = await platform_owner_client.post(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
            json={
                "email": user_email,
                "first_name": "CrossTenant",
                "last_name": "User",
                "password": "crosspassword123",
                "role_id": str(tenant_b_role.id),
                "send_credentials": False,
            },
        )
        assert create_resp.status_code == 201
        new_user = create_resp.json()
        assert new_user["tenant_id"] == str(tenant_b.id)

        # Step 2: Platform owner lists users in tenant_b (should see the new user)
        list_resp = await platform_owner_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert list_resp.status_code == 200
        emails = [u["email"] for u in list_resp.json()["items"]]
        assert user_email in emails

        # Step 3: Platform owner updates user in tenant_b
        update_resp = await platform_owner_client.patch(
            f"/api/v1/auth/users/{new_user['id']}",
            params={"tenant_id": str(tenant_b.id)},
            json={"first_name": "UpdatedCross", "version": 1},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["first_name"] == "UpdatedCross"

        # Step 4: Site owner (from test_tenant) CANNOT access tenant_b users
        isolation_resp = await site_owner_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert isolation_resp.status_code == 403
        assert "permission_denied" in isolation_resp.json()["detail"]["type"]

        # Step 5: Site owner cannot create user in tenant_b
        site_create_resp = await site_owner_client.post(
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
        assert site_create_resp.status_code == 403

        # Step 6: User created in tenant_b can login to tenant_b
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "crosspassword123"},
            headers={"X-Tenant-ID": str(tenant_b.id)},
        )
        assert login_resp.status_code == 200

        # Step 7: Platform owner deletes user in tenant_b
        delete_resp = await platform_owner_client.delete(
            f"/api/v1/auth/users/{new_user['id']}",
            params={"tenant_id": str(tenant_b.id)},
        )
        assert delete_resp.status_code == 204

        # Step 8: Deleted user can no longer login
        login_blocked = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "crosspassword123"},
            headers={"X-Tenant-ID": str(tenant_b.id)},
        )
        assert login_blocked.status_code == 401
