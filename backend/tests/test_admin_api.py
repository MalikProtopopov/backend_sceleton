"""Tests for admin API endpoints (require authentication)."""

import pytest
from httpx import AsyncClient


# Note: These tests check that endpoints require authentication.
# Full integration tests would need a test user and valid tokens.


@pytest.mark.asyncio
async def test_list_users_unauthorized(client: AsyncClient) -> None:
    """Test users list requires authentication."""
    response = await client.get("/api/v1/auth/users")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_services_admin_unauthorized(client: AsyncClient) -> None:
    """Test admin services list requires authentication."""
    response = await client.get("/api/v1/admin/services")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_articles_admin_unauthorized(client: AsyncClient) -> None:
    """Test admin articles list requires authentication."""
    response = await client.get("/api/v1/admin/articles")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_inquiries_admin_unauthorized(client: AsyncClient) -> None:
    """Test admin inquiries list requires authentication."""
    response = await client.get("/api/v1/admin/inquiries")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_seo_routes_unauthorized(client: AsyncClient) -> None:
    """Test SEO routes list requires authentication."""
    response = await client.get("/api/v1/admin/seo/routes")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_files_unauthorized(client: AsyncClient) -> None:
    """Test files list requires authentication."""
    response = await client.get("/api/v1/admin/files")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_feature_flags_requires_tenant_id(client: AsyncClient) -> None:
    """Test feature flags requires tenant_id parameter."""
    # Without tenant_id, should return 422 (validation error)
    response = await client.get("/api/v1/admin/feature-flags")
    assert response.status_code == 422

    # With tenant_id, should return 200
    response = await client.get(
        "/api/v1/admin/feature-flags",
        params={"tenant_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 200

