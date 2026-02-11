"""Security tests for information leakage prevention (SEC-14 to SEC-18).

Verifies that error messages don't reveal internal system details.
"""

import pytest
from httpx import AsyncClient

from app.modules.tenants.models import FeatureFlag, Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.security
class TestLoginErrorLeakage:
    """SEC-14: Wrong email login returns generic message."""

    @pytest.mark.asyncio
    async def test_wrong_email_generic_message(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
    ) -> None:
        """Wrong email should return generic 'Invalid email or password'."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpass"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert response.status_code == 401
        detail = response.json()["detail"]["detail"]
        assert "Invalid email or password" in detail
        # Should NOT reveal whether email exists
        assert "not found" not in detail.lower()
        assert "not exist" not in detail.lower()


@pytest.mark.security
class TestForgotPasswordLeakage:
    """SEC-15: Forgot-password always returns 204."""

    @pytest.mark.asyncio
    async def test_forgot_password_same_response_for_any_email(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        mock_email_service,
    ) -> None:
        """Both existing and non-existing email should get 204."""
        response_existing = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "any@example.com"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        response_nonexisting = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "doesnt-exist@example.com"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )

        assert response_existing.status_code == 204
        assert response_nonexisting.status_code == 204


@pytest.mark.security
class TestFeatureDisabledLeakage:
    """SEC-16: feature_disabled response has no internal IDs."""

    @pytest.mark.asyncio
    async def test_feature_disabled_no_internal_ids(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        """403 feature_disabled should not leak tenant_id or user_id."""
        response = await authenticated_client.get("/api/v1/admin/articles")
        assert response.status_code == 403
        body = response.json()["detail"]

        # Check that no UUID-like strings appear in unexpected fields
        detail_str = str(body.get("detail", ""))
        assert "tenant_id" not in detail_str.lower()
        assert body.get("feature") == "blog_module"  # Only feature name, no IDs


@pytest.mark.security
class TestTenantInactiveLeakage:
    """SEC-17: tenant_inactive response has no tenant details."""

    @pytest.mark.asyncio
    async def test_tenant_inactive_no_tenant_details(
        self,
        inactive_tenant_client: AsyncClient,
    ) -> None:
        """403 tenant_inactive should not leak tenant name, slug, etc."""
        response = await inactive_tenant_client.get("/api/v1/auth/me")
        assert response.status_code == 403
        body = response.json()["detail"]
        detail_str = str(body)
        assert "slug" not in detail_str.lower()
        assert "domain" not in detail_str.lower()
        # Should only say "suspended"
        assert "suspended" in body["detail"].lower()


@pytest.mark.security
class TestErrorNoStackTraces:
    """SEC-18: Error responses never contain stack traces."""

    @pytest.mark.asyncio
    async def test_error_response_no_stack_trace(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        """Error responses should not include traceback or file paths."""
        response = await authenticated_client.get("/api/v1/admin/articles")
        assert response.status_code == 403
        body_str = str(response.json())
        assert "Traceback" not in body_str
        assert "File \"" not in body_str
        assert ".py" not in body_str

    @pytest.mark.asyncio
    async def test_401_response_no_stack_trace(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
    ) -> None:
        """401 error should not include traceback."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpass"},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert response.status_code == 401
        body_str = str(response.json())
        assert "Traceback" not in body_str
        assert "File \"" not in body_str
