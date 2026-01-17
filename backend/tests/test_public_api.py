"""Tests for public API endpoints."""

import pytest
from httpx import AsyncClient


# ============================================================================
# Company Public API
# ============================================================================


@pytest.mark.asyncio
async def test_list_services_public(client: AsyncClient) -> None:
    """Test public services list endpoint."""
    response = await client.get(
        "/api/v1/public/services",
        params={
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "locale": "ru",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_employees_public(client: AsyncClient) -> None:
    """Test public employees list endpoint."""
    response = await client.get(
        "/api/v1/public/employees",
        params={
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "locale": "ru",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_advantages_public(client: AsyncClient) -> None:
    """Test public advantages list endpoint."""
    response = await client.get(
        "/api/v1/public/advantages",
        params={
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "locale": "ru",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_contacts_public(client: AsyncClient) -> None:
    """Test public contacts endpoint."""
    response = await client.get(
        "/api/v1/public/contacts",
        params={"tenant_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "addresses" in data
    assert "contacts" in data


# ============================================================================
# Content Public API
# ============================================================================


@pytest.mark.asyncio
async def test_list_articles_public(client: AsyncClient) -> None:
    """Test public articles list endpoint."""
    response = await client.get(
        "/api/v1/public/articles",
        params={
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "locale": "ru",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_list_topics_public(client: AsyncClient) -> None:
    """Test public topics list endpoint."""
    response = await client.get(
        "/api/v1/public/topics",
        params={
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "locale": "ru",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_faq_public(client: AsyncClient) -> None:
    """Test public FAQ list endpoint."""
    response = await client.get(
        "/api/v1/public/faq",
        params={
            "tenant_id": "00000000-0000-0000-0000-000000000000",
            "locale": "ru",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ============================================================================
# Leads Public API
# ============================================================================


@pytest.mark.asyncio
async def test_create_inquiry_public(client: AsyncClient, test_tenant) -> None:
    """Test creating public inquiry."""
    response = await client.post(
        "/api/v1/public/inquiries",
        params={"tenant_id": str(test_tenant.id)},
        json={
            "name": "Test User",
            "email": "test@example.com",
            "phone": "+7 999 123 4567",
            "message": "Test message",
            "analytics": {
                "utm_source": "google",
                "utm_medium": "cpc",
                "device_type": "desktop",
            },
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert data["utm_source"] == "google"
    assert data["status"] == "new"


@pytest.mark.asyncio
async def test_create_inquiry_minimal(client: AsyncClient, test_tenant) -> None:
    """Test creating inquiry with minimal data."""
    response = await client.post(
        "/api/v1/public/inquiries",
        params={"tenant_id": str(test_tenant.id)},
        json={
            "name": "Minimal User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Minimal User"


@pytest.mark.asyncio
async def test_create_inquiry_missing_name(client: AsyncClient) -> None:
    """Test inquiry creation fails without name."""
    response = await client.post(
        "/api/v1/public/inquiries",
        params={"tenant_id": "00000000-0000-0000-0000-000000000000"},
        json={
            "email": "test@example.com",
            # Missing name
        },
    )

    assert response.status_code == 422


# ============================================================================
# SEO Public API
# ============================================================================


@pytest.mark.asyncio
async def test_get_seo_meta(client: AsyncClient) -> None:
    """Test getting SEO meta for a path."""
    response = await client.get(
        "/api/v1/public/seo/meta",
        params={
            "path": "/about",
            "locale": "ru",
            "tenant_id": "00000000-0000-0000-0000-000000000000",
        },
    )

    assert response.status_code == 200
    data = response.json()
    # Returns empty defaults if no SEO route exists
    assert "robots" in data


@pytest.mark.asyncio
async def test_get_sitemap(client: AsyncClient) -> None:
    """Test sitemap.xml generation."""
    response = await client.get(
        "/api/v1/public/sitemap.xml",
        params={
            "locale": "ru",
            "tenant_id": "00000000-0000-0000-0000-000000000000",
        },
    )

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<?xml" in response.text
    assert "<urlset" in response.text


@pytest.mark.asyncio
async def test_get_robots(client: AsyncClient) -> None:
    """Test robots.txt generation."""
    response = await client.get(
        "/api/v1/public/robots.txt",
        params={"tenant_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert "User-agent" in response.text
    assert "Sitemap" in response.text

