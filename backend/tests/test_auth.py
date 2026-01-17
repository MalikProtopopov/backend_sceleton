"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, test_tenant) -> None:
    """Test login with invalid credentials returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": str(test_tenant.id)},
        json={
            "email": "invalid@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert data["type"].endswith("invalid_credentials")


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient, test_tenant) -> None:
    """Test login with missing fields returns 422."""
    response = await client.post(
        "/api/v1/auth/login",
        headers={"X-Tenant-ID": str(test_tenant.id)},
        json={
            "email": "test@example.com",
            # Missing password
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient) -> None:
    """Test refresh with invalid token returns 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_unauthorized(client: AsyncClient) -> None:
    """Test /me endpoint without auth returns 401."""
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401

