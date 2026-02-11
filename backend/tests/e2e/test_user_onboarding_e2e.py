"""E2E test: User onboarding flow.

Scenario 5: Create user with send_credentials -> login -> see force_password_change
-> change password -> verify force_password_change cleared.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.auth.models import Role
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.e2e
class TestUserOnboardingE2E:
    """Full user onboarding: create -> login -> change password."""

    @pytest.mark.asyncio
    async def test_full_user_onboarding_flow(
        self,
        platform_owner_client: AsyncClient,
        client: AsyncClient,
        test_tenant: Tenant,
        test_role: Role,
        mock_email_service,
    ) -> None:
        """E2E Scenario 5: Complete user onboarding."""

        initial_password = "initialpassword123"
        new_password = "newstrongpassword456"
        user_email = f"onboarding-{uuid4().hex[:8]}@example.com"

        # Step 1: Platform owner creates user with send_credentials=true
        create_resp = await platform_owner_client.post(
            "/api/v1/auth/users",
            json={
                "email": user_email,
                "first_name": "Onboard",
                "last_name": "User",
                "password": initial_password,
                "role_id": str(test_role.id),
                "send_credentials": True,
            },
        )
        assert create_resp.status_code == 201
        assert create_resp.json()["force_password_change"] is True

        # Step 2: Verify welcome email was sent (not containing password)
        mock_email_service["welcome"].assert_called_once()
        call_kwargs = mock_email_service["welcome"].call_args.kwargs
        assert initial_password not in str(call_kwargs)

        # Step 3: New user logs in
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": initial_password},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert login_data["user"]["force_password_change"] is True
        access_token = login_data["tokens"]["access_token"]

        # Step 4: Check /me shows force_password_change
        me_resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["force_password_change"] is True

        # Step 5: User changes password
        change_resp = await client.post(
            "/api/v1/auth/me/password",
            json={
                "current_password": initial_password,
                "new_password": new_password,
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert change_resp.status_code == 204

        # Step 6: Login with new password and verify force_password_change cleared
        new_login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": new_password},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert new_login_resp.status_code == 200
        assert new_login_resp.json()["user"]["force_password_change"] is False
