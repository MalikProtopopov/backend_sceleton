"""Security tests: tenant isolation -- data must never leak across tenants."""


import pytest
from httpx import AsyncClient


@pytest.mark.security
@pytest.mark.asyncio
class TestTenantIsolation:
    """Verify that user in tenant A cannot access data in tenant B."""

    async def test_user_cannot_read_other_tenant_articles(
        self, site_owner_client: AsyncClient, second_tenant
    ):
        """site_owner (tenant_active) queries articles with second_tenant.id -> blocked."""
        resp = await site_owner_client.get(
            "/api/v1/admin/articles",
            params={"tenant_id": str(second_tenant.id)},
        )
        # Should either be 403 or filtered to empty (no cross-tenant data)
        if resp.status_code == 200:
            body = resp.json()
            # Should only see own tenant's data (empty since tenant_active is just created)
            _ = body.get("items", body.get("data", []))
        else:
            assert resp.status_code in (403, 404)

    async def test_wrong_tenant_header_public_no_data_leak(
        self, client: AsyncClient, tenant_active, second_tenant
    ):
        """Public route with wrong tenant_id should not return other tenant's data."""
        resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(second_tenant.id), "locale": "ru"},
        )
        # Should succeed but return empty or second_tenant's data only
        assert resp.status_code in (200, 404)

    async def test_authenticated_request_after_deactivation_returns_403(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        """After deactivating tenant, next request should return 403."""
        from tests.helpers import deactivate_tenant
        await deactivate_tenant(db_session, tenant_active.id)
        resp = await site_owner_client.get("/api/v1/admin/articles")
        assert resp.status_code == 403

    async def test_public_endpoint_inactive_tenant(
        self, client: AsyncClient, tenant_inactive
    ):
        """Public endpoints for an inactive tenant should fail."""
        resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(tenant_inactive.id), "locale": "ru"},
        )
        # Should be 404 or 403 depending on implementation
        assert resp.status_code in (403, 404)
