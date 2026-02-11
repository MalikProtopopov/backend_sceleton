"""Integration tests for password reset flow (Phase 7).

T7-01 to T7-06: forgot-password, reset-password, token expiry, force_password_change.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_password_reset_token
from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.integration
class TestForgotPassword:
    """T7-01, T7-02: Forgot password returns 204 for any email."""

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        mock_email_service,
    ) -> None:
        """Existing user should get 204 and reset email sent."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": test_user.email},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert response.status_code == 204
        mock_email_service["reset"].assert_called_once()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        mock_email_service,
    ) -> None:
        """Nonexistent email should still return 204 (no error leaked)."""
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert response.status_code == 204
        mock_email_service["reset"].assert_not_called()


@pytest.mark.integration
class TestResetPassword:
    """T7-03 to T7-06: Reset password with valid/expired/wrong tokens."""

    @pytest.mark.asyncio
    async def test_reset_password_with_valid_token(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
    ) -> None:
        """Valid reset token should allow password change."""
        token = create_password_reset_token(
            str(test_user.id), str(test_tenant.id), test_user.email,
        )
        new_password = "brandnewpassword123"

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": new_password},
        )
        assert response.status_code == 204

        # Verify login with new password works
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": new_password},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert login_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Expired reset token should return 401."""
        from freezegun import freeze_time

        with freeze_time("2026-01-01 12:00:00"):
            token = create_password_reset_token(
                str(uuid4()), str(uuid4()), "test@example.com",
            )

        with freeze_time("2026-01-01 14:00:00"):
            response = await client.post(
                "/api/v1/auth/reset-password",
                json={"token": token, "new_password": "newpassword123"},
            )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_wrong_token_type(
        self,
        client: AsyncClient,
    ) -> None:
        """Using access token as reset token should fail."""
        from app.core.security import create_access_token

        access_token = create_access_token({
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "email": "test@example.com",
        })

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": access_token, "new_password": "newpassword123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_clears_force_password_change(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        force_pwd_user: AdminUser,
        db_session: AsyncSession,
    ) -> None:
        """Password reset should clear force_password_change flag."""
        token = create_password_reset_token(
            str(force_pwd_user.id), str(test_tenant.id), force_pwd_user.email,
        )

        response = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": token, "new_password": "resetpassword123"},
        )
        assert response.status_code == 204

        await db_session.refresh(force_pwd_user)
        assert force_pwd_user.force_password_change is False
