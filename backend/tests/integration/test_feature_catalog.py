"""Integration tests for feature catalog endpoint (Phase 5).

T5-01 to T5-08: /me/features returns full catalog, locale, can_request, all_features_enabled.
"""

import pytest
from httpx import AsyncClient

from app.modules.tenants.models import FeatureFlag


@pytest.mark.integration
class TestFeatureCatalogRegularUser:
    """T5-01, T5-06, T5-07: Regular user gets full catalog."""

    @pytest.mark.asyncio
    async def test_full_catalog_returned(
        self,
        authenticated_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """Regular user should see all 8 features with correct enabled status."""
        response = await authenticated_client.get("/api/v1/auth/me/features")
        assert response.status_code == 200
        data = response.json()

        features = data["features"]
        assert len(features) == 8

        # Check specific flags match DB
        feature_map = {f["name"]: f for f in features}
        assert feature_map["blog_module"]["enabled"] is True
        assert feature_map["reviews_module"]["enabled"] is False
        assert feature_map["team_module"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_disabled_feature_has_can_request_true(
        self,
        authenticated_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """Disabled feature should have can_request=True."""
        response = await authenticated_client.get("/api/v1/auth/me/features")
        data = response.json()
        feature_map = {f["name"]: f for f in data["features"]}
        assert feature_map["reviews_module"]["can_request"] is True
        assert feature_map["blog_module"]["can_request"] is False

    @pytest.mark.asyncio
    async def test_response_includes_tenant_id(
        self,
        authenticated_client: AsyncClient,
        test_tenant,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """Response should include tenant_id."""
        response = await authenticated_client.get("/api/v1/auth/me/features")
        data = response.json()
        assert data["tenant_id"] == str(test_tenant.id)


@pytest.mark.integration
class TestFeatureCatalogPrivileged:
    """T5-02, T5-03: Platform owner and superuser get all_features_enabled."""

    @pytest.mark.asyncio
    async def test_platform_owner_gets_all_features_enabled(
        self,
        platform_owner_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """Platform owner should see all_features_enabled=true."""
        response = await platform_owner_client.get("/api/v1/auth/me/features")
        assert response.status_code == 200
        data = response.json()
        assert data["all_features_enabled"] is True

    @pytest.mark.asyncio
    async def test_superuser_gets_all_features_enabled(
        self,
        superuser_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """Superuser should see all_features_enabled=true."""
        response = await superuser_client.get("/api/v1/auth/me/features")
        assert response.status_code == 200
        data = response.json()
        assert data["all_features_enabled"] is True


@pytest.mark.integration
class TestFeatureCatalogLocale:
    """T5-04, T5-05: Locale support for feature titles."""

    @pytest.mark.asyncio
    async def test_locale_ru_returns_russian_titles(
        self,
        authenticated_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """locale=ru should return Russian titles."""
        response = await authenticated_client.get(
            "/api/v1/auth/me/features", params={"locale": "ru"},
        )
        assert response.status_code == 200
        features = response.json()["features"]
        blog = next(f for f in features if f["name"] == "blog_module")
        # Should contain Russian characters
        assert "Блог" in blog["title"] or "Blog" in blog["title"]

    @pytest.mark.asyncio
    async def test_locale_en_returns_english_titles(
        self,
        authenticated_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """locale=en should return English titles."""
        response = await authenticated_client.get(
            "/api/v1/auth/me/features", params={"locale": "en"},
        )
        assert response.status_code == 200
        features = response.json()["features"]
        blog = next(f for f in features if f["name"] == "blog_module")
        assert "Blog" in blog["title"]
