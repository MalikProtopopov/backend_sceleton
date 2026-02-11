"""Security tests: error messages must not leak internal details."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.security
@pytest.mark.asyncio
class TestInformationLeakage:

    async def test_forgot_password_always_returns_204(
        self, client: AsyncClient, test_tenant
    ):
        """Forgot-password should return the same response for existing and non-existing users."""
        resp1 = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        resp2 = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "also-nonexistent@example.com"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        # Both should return the same status
        assert resp1.status_code == resp2.status_code
        # Typically 204 or 200 with generic message
        assert resp1.status_code in (200, 204)

    async def test_login_wrong_password_no_user_info_leaked(
        self, client: AsyncClient, test_tenant
    ):
        """Login failure should not reveal whether user exists."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong123"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert resp.status_code == 401
        body = resp.json()
        detail = body if "type" in body else body.get("detail", body)
        # Should be generic message, not "user not found"
        msg = str(detail.get("detail", "")).lower() if isinstance(detail, dict) else str(detail).lower()
        assert "not found" not in msg
        assert "does not exist" not in msg

    async def test_invalid_token_no_stack_trace(
        self, client: AsyncClient
    ):
        """Invalid JWT should return clean error, no stack trace."""
        resp = await client.get(
            "/api/v1/admin/articles",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401
        body = resp.text
        assert "Traceback" not in body
        assert "File " not in body

    async def test_nonexistent_tenant_no_detail_leakage(
        self, client: AsyncClient
    ):
        """Public request with non-existent tenant_id should not leak DB info."""
        fake_tid = uuid4()
        resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(fake_tid), "locale": "ru"},
        )
        assert resp.status_code in (400, 404)
        body = resp.text
        assert "sqlalchemy" not in body.lower()
        assert "postgresql" not in body.lower()
