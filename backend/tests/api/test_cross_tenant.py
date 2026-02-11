"""API tests: cross-tenant user management -- platform_owner vs site_owner."""

import pytest
from httpx import AsyncClient

from tests.helpers import assert_error_response


@pytest.mark.api
@pytest.mark.asyncio
class TestCrossTenantAccess:

    async def test_platform_owner_list_users_cross_tenant(
        self, platform_owner_client: AsyncClient, second_tenant
    ):
        resp = await platform_owner_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(second_tenant.id)},
        )
        assert resp.status_code == 200

    async def test_site_owner_list_users_cross_tenant_returns_403(
        self, site_owner_client: AsyncClient, second_tenant
    ):
        resp = await site_owner_client.get(
            "/api/v1/auth/users",
            params={"tenant_id": str(second_tenant.id)},
        )
        assert_error_response(resp, 403, "permission_denied")

    async def test_platform_owner_create_user_cross_tenant(
        self, platform_owner_client: AsyncClient, second_tenant
    ):
        from uuid import uuid4
        resp = await platform_owner_client.post(
            "/api/v1/auth/users",
            params={"tenant_id": str(second_tenant.id)},
            json={
                "email": f"cross-{uuid4().hex[:8]}@example.com",
                "password": "SecurePass123!",
                "first_name": "Cross",
                "last_name": "Tenant",
                "send_credentials": False,
            },
        )
        assert resp.status_code in (200, 201)

    async def test_site_owner_create_user_cross_tenant_returns_403(
        self, site_owner_client: AsyncClient, second_tenant
    ):
        resp = await site_owner_client.post(
            "/api/v1/auth/users",
            params={"tenant_id": str(second_tenant.id)},
            json={
                "email": "blocked@test.local",
                "password": "SecurePass123!",
                "first_name": "Blocked",
                "last_name": "User",
                "send_credentials": False,
            },
        )
        assert_error_response(resp, 403, "permission_denied")
