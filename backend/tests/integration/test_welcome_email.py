"""Integration tests for welcome email flow (Phase 4).

T4-04, T4-05, T4-07, T4-09: force_password_change in responses, no password in email.
"""

import pytest
from httpx import AsyncClient

from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.integration
class TestForcePasswordChangeInResponses:
    """T4-04, T4-05, T4-09: force_password_change flag in API responses."""

    @pytest.mark.asyncio
    async def test_login_response_includes_force_password_change(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        force_pwd_user: AdminUser,
    ) -> None:
        """Login response should include force_password_change=true."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": force_pwd_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert response.status_code == 200
        user_data = response.json()["user"]
        assert user_data["force_password_change"] is True

    @pytest.mark.asyncio
    async def test_me_returns_force_password_change(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        force_pwd_user: AdminUser,
    ) -> None:
        """GET /me should include force_password_change."""
        # Login first to get token
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": force_pwd_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        token = login_resp.json()["tokens"]["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["force_password_change"] is True

    @pytest.mark.asyncio
    async def test_user_response_includes_force_password_change(
        self,
        platform_owner_client: AsyncClient,
        force_pwd_user: AdminUser,
    ) -> None:
        """GET /users/{id} should include force_password_change field."""
        response = await platform_owner_client.get(
            f"/api/v1/auth/users/{force_pwd_user.id}",
        )
        assert response.status_code == 200
        assert "force_password_change" in response.json()


@pytest.mark.integration
class TestWelcomeEmailSecurity:
    """T4-07: Welcome email does NOT contain password."""

    @pytest.mark.asyncio
    async def test_welcome_email_no_password_in_args(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        test_role,
        mock_email_service,
    ) -> None:
        """Creating user with send_credentials=true should send email without password."""
        response = await platform_owner_client.post(
            "/api/v1/auth/users",
            json={
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password": "secretpassword123",
                "role_id": str(test_role.id),
                "send_credentials": True,
            },
        )
        assert response.status_code == 201

        # Verify email was sent
        mock_email_service["welcome"].assert_called_once()
        call_kwargs = mock_email_service["welcome"].call_args.kwargs
        # Verify password is NOT in the email arguments
        assert "password" not in call_kwargs
        assert "secretpassword123" not in str(call_kwargs)
