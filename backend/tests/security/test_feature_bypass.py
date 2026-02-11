"""Security tests for feature flag bypass (SEC-06 to SEC-08).

Verifies that disabled features cannot be accessed via direct URL.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.modules.tenants.models import FeatureFlag


@pytest.mark.security
class TestFeatureFlagBypass:
    """SEC-06 to SEC-08: Direct access to disabled module endpoints."""

    @pytest.mark.asyncio
    async def test_direct_get_to_disabled_reviews(
        self,
        authenticated_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """SEC-06: GET /admin/reviews when reviews_module=False -> 403."""
        response = await authenticated_client.get("/api/v1/admin/reviews")
        assert response.status_code == 403
        assert "feature_disabled" in response.json()["detail"]["type"]

    @pytest.mark.asyncio
    async def test_direct_post_to_disabled_cases(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        """SEC-07: POST /admin/cases when cases_module=False -> 403."""
        response = await authenticated_client.post(
            "/api/v1/admin/cases",
            json={"slug": "test-case", "locales": {}},
        )
        assert response.status_code == 403
        assert "feature_disabled" in response.json()["detail"]["type"]

    @pytest.mark.asyncio
    async def test_bulk_operation_disabled_resource(
        self,
        authenticated_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """SEC-08: Bulk op with resource_type=reviews (disabled) -> 403."""
        response = await authenticated_client.post(
            "/api/v1/admin/bulk",
            json={
                "resource_type": "reviews",
                "action": "publish",
                "ids": [str(uuid4())],
            },
        )
        assert response.status_code == 403
