"""Integration tests for tenant list search and sort (Phase 7).

T7-11 + T3-08, T3-09: Default sort, sort by name, search by name.
"""

import pytest
from httpx import AsyncClient

from app.modules.tenants.models import Tenant


@pytest.mark.integration
class TestTenantListDefaultSort:
    """T7-11: Default sort by created_at desc."""

    @pytest.mark.asyncio
    async def test_default_sort_created_at_desc(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """Default tenant list should be sorted by created_at desc."""
        response = await platform_owner_client.get("/api/v1/tenants")
        assert response.status_code == 200
        items = response.json()["items"]
        if len(items) >= 2:
            dates = [t["created_at"] for t in items]
            assert dates == sorted(dates, reverse=True)


@pytest.mark.integration
class TestTenantListSort:
    """Sort by name."""

    @pytest.mark.asyncio
    async def test_sort_by_name_asc(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """Sorting by name asc should order alphabetically."""
        response = await platform_owner_client.get(
            "/api/v1/tenants",
            params={"sort_by": "name", "sort_order": "asc"},
        )
        assert response.status_code == 200
        items = response.json()["items"]
        if len(items) >= 2:
            names = [t["name"] for t in items]
            assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_sort_by_name_desc(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """Sorting by name desc should order reverse alphabetically."""
        response = await platform_owner_client.get(
            "/api/v1/tenants",
            params={"sort_by": "name", "sort_order": "desc"},
        )
        assert response.status_code == 200
        items = response.json()["items"]
        if len(items) >= 2:
            names = [t["name"] for t in items]
            assert names == sorted(names, reverse=True)


@pytest.mark.integration
class TestTenantListSearch:
    """Search by name substring."""

    @pytest.mark.asyncio
    async def test_search_by_name(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        tenant_b: Tenant,
    ) -> None:
        """Search should filter tenants by name substring."""
        response = await platform_owner_client.get(
            "/api/v1/tenants",
            params={"search": "Tenant B"},
        )
        assert response.status_code == 200
        items = response.json()["items"]
        for item in items:
            assert "Tenant B" in item["name"]

    @pytest.mark.asyncio
    async def test_search_no_results(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
    ) -> None:
        """Search with no matches should return empty list."""
        response = await platform_owner_client.get(
            "/api/v1/tenants",
            params={"search": "NonexistentCompany12345"},
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0
