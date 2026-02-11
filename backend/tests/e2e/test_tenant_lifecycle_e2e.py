"""E2E test: Full tenant lifecycle.

Scenario 1: Create tenant -> create user -> enable features -> deactivate -> verify lockout.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.auth.models import AdminUser, Role
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.e2e
class TestTenantLifecycleE2E:
    """Full tenant lifecycle: create -> configure -> deactivate -> lockout."""

    @pytest.mark.asyncio
    async def test_full_tenant_lifecycle(
        self,
        platform_owner_client: AsyncClient,
        client: AsyncClient,
        db_session: AsyncSession,
        mock_email_service,
    ) -> None:
        """E2E Scenario 1: Complete tenant lifecycle."""

        # Step 1: Create a new tenant
        create_resp = await platform_owner_client.post(
            "/api/v1/tenants",
            json={
                "name": f"E2E Tenant {uuid4().hex[:8]}",
                "slug": f"e2e-{uuid4().hex[:8]}",
                "plan": "pro",
            },
        )
        assert create_resp.status_code == 201
        new_tenant = create_resp.json()
        tenant_id = new_tenant["id"]

        # Step 2: Enable features for the new tenant
        for feature in ["blog_module", "cases_module", "faq_module"]:
            flag_resp = await platform_owner_client.patch(
                f"/api/v1/feature-flags/{feature}",
                params={"tenant_id": tenant_id},
                json={"enabled": True},
            )
            assert flag_resp.status_code == 200

        # Step 3: Create a role in the new tenant
        # We need to create a role first (via DB since API might not expose this easily)
        role = Role(
            id=uuid4(),
            tenant_id=tenant_id,
            name=f"admin-e2e-{uuid4().hex[:8]}",
            description="E2E Test Admin",
        )
        db_session.add(role)
        await db_session.flush()

        # Step 4: Create a user in the new tenant
        user_email = f"e2e-user-{uuid4().hex[:8]}@example.com"
        user_resp = await platform_owner_client.post(
            "/api/v1/auth/users",
            params={"tenant_id": tenant_id},
            json={
                "email": user_email,
                "first_name": "E2E",
                "last_name": "User",
                "password": "e2epassword123",
                "role_id": str(role.id),
                "send_credentials": False,
            },
        )
        assert user_resp.status_code == 201
        new_user = user_resp.json()

        # Step 5: User can login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "e2epassword123"},
            headers={"X-Tenant-ID": tenant_id},
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()["tokens"]

        # Step 6: User can access /me
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert me_resp.status_code == 200

        # Step 7: Deactivate the tenant
        deactivate_resp = await platform_owner_client.patch(
            f"/api/v1/tenants/{tenant_id}",
            json={"is_active": False, "version": 1},
        )
        assert deactivate_resp.status_code == 200

        # Step 8: Verify lockout — existing token should be rejected
        lockout_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert lockout_resp.status_code == 403
        assert "tenant_inactive" in lockout_resp.json()["detail"]["type"]

        # Step 9: Verify lockout — new login should be rejected
        login_blocked_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "e2epassword123"},
            headers={"X-Tenant-ID": tenant_id},
        )
        assert login_blocked_resp.status_code == 403
