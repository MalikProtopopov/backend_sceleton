"""Security tests for token validity after tenant deactivation (SEC-09, SEC-10).

Verifies that access and refresh tokens stop working when tenant is deactivated.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.security
class TestTokenAfterTenantDeactivation:
    """SEC-09, SEC-10: Tokens invalidated when tenant deactivated."""

    @pytest.mark.asyncio
    async def test_access_token_rejected_after_tenant_deactivation(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """SEC-09: Login -> deactivate -> use access token -> 403 tenant_inactive."""
        # Verify access works
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200

        # Deactivate tenant
        test_tenant.is_active = False
        await db_session.flush()

        # Token should be rejected
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 403
        assert "tenant_inactive" in response.json()["detail"]["type"]

    @pytest.mark.asyncio
    async def test_refresh_token_rejected_after_tenant_deactivation(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        db_session: AsyncSession,
    ) -> None:
        """SEC-10: Login -> deactivate -> refresh token -> 403 tenant_inactive."""
        # Login to get tokens
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["tokens"]["refresh_token"]

        # Deactivate tenant
        test_tenant.is_active = False
        await db_session.flush()

        # Refresh should be rejected
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 403
        assert "tenant_inactive" in response.json()["detail"]["type"]
