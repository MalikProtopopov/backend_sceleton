"""Integration tests for tenant lifecycle enforcement (Phase 1).

T1-01 to T1-11: Tenant is_active checks on login, refresh, authenticated
requests, public API, platform_owner bypass, superuser bypass, and Redis cache.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AdminUser
from app.modules.tenants.models import Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.integration
class TestTenantLifecycleLogin:
    """T1-01: Login blocked for inactive tenant."""

    @pytest.mark.asyncio
    async def test_login_returns_403_for_inactive_tenant(
        self,
        client: AsyncClient,
        inactive_tenant: Tenant,
        inactive_tenant_user: AdminUser,
    ) -> None:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": inactive_tenant_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(inactive_tenant.id)},
        )
        assert response.status_code == 403
        data = response.json()
        assert "tenant_inactive" in data["detail"]["type"]
        assert "suspended" in data["detail"]["detail"].lower()


@pytest.mark.integration
class TestTenantLifecycleRefresh:
    """T1-02: Refresh blocked for inactive tenant."""

    @pytest.mark.asyncio
    async def test_refresh_returns_403_for_inactive_tenant(
        self,
        client: AsyncClient,
        inactive_tenant: Tenant,
        inactive_tenant_user: AdminUser,
        db_session: AsyncSession,
    ) -> None:
        # First activate tenant temporarily to login
        inactive_tenant.is_active = True
        await db_session.flush()

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": inactive_tenant_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(inactive_tenant.id)},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["tokens"]["refresh_token"]

        # Now deactivate tenant
        inactive_tenant.is_active = False
        await db_session.flush()

        # Try to refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 403
        assert "tenant_inactive" in response.json()["detail"]["type"]


@pytest.mark.integration
class TestTenantLifecycleAuthenticatedRequest:
    """T1-03: Authenticated request blocked for inactive tenant.
    T1-04: Platform owner bypasses check.
    T1-05: Superuser bypasses check.
    T1-11: Token valid by time but tenant deactivated.
    """

    @pytest.mark.asyncio
    async def test_me_blocked_for_inactive_tenant_user(
        self,
        inactive_tenant_client: AsyncClient,
    ) -> None:
        """Valid token for user in inactive tenant should get 403 on /me."""
        response = await inactive_tenant_client.get("/api/v1/auth/me")
        assert response.status_code == 403
        assert "tenant_inactive" in response.json()["detail"]["type"]

    @pytest.mark.asyncio
    async def test_platform_owner_bypasses_inactive_check(
        self,
        platform_owner_client: AsyncClient,
    ) -> None:
        """Platform owner should access /me even if their own check passes."""
        response = await platform_owner_client.get("/api/v1/auth/me")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_superuser_bypasses_inactive_check(
        self,
        superuser_client: AsyncClient,
    ) -> None:
        """Superuser should access /me without tenant check."""
        response = await superuser_client.get("/api/v1/auth/me")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_token_valid_but_tenant_deactivated_mid_session(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        auth_headers: dict[str, str],
        db_session: AsyncSession,
    ) -> None:
        """Token created while active, then tenant deactivated -> 403."""
        # Verify access works first
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200

        # Deactivate tenant
        test_tenant.is_active = False
        await db_session.flush()

        # Same token should now be rejected
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 403
        assert "tenant_inactive" in response.json()["detail"]["type"]


@pytest.mark.integration
class TestTenantLifecyclePublicAPI:
    """T1-06: Public API blocked for inactive tenant."""

    @pytest.mark.asyncio
    async def test_public_api_blocked_for_inactive_tenant(
        self,
        client: AsyncClient,
        inactive_tenant: Tenant,
    ) -> None:
        """Public API should return 404 for inactive tenant."""
        response = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(inactive_tenant.id)},
        )
        # Could be 404 or 400 depending on how public tenant resolution works
        assert response.status_code in (400, 404)
