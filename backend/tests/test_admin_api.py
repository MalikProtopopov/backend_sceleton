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
async def test_feature_flags_requires_auth(client: AsyncClient) -> None:
    """Test feature flags endpoint requires authentication."""
    # Without auth token, should return 401
    response = await client.get("/api/v1/feature-flags")
    assert response.status_code == 401

