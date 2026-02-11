"""Integration tests for feature flag route coverage (Phase 2).

T2-01 to T2-12: require_feature on admin routes, error messages, superuser bypass.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenants.models import FeatureFlag, Tenant


@pytest.mark.integration
class TestFeatureFlagBlogModule:
    """T2-01, T2-02, T2-09: Blog module (articles, topics) admin routes."""

    @pytest.mark.asyncio
    async def test_articles_admin_blocked_when_blog_disabled(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        """GET /admin/articles should return 403 when blog_module is disabled."""
        response = await authenticated_client.get("/api/v1/admin/articles")
        assert response.status_code == 403
        data = response.json()["detail"]
        assert "feature_disabled" in data["type"]
        assert data["feature"] == "blog_module"
        assert data["contact_admin"] is True

    @pytest.mark.asyncio
    async def test_topics_admin_blocked_when_blog_disabled(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        """POST /admin/topics should return 403 when blog_module is disabled."""
        response = await authenticated_client.post(
            "/api/v1/admin/topics",
            json={"slug": "test", "sort_order": 0, "locales": {}},
        )
        assert response.status_code == 403
        data = response.json()["detail"]
        assert data["feature"] == "blog_module"

    @pytest.mark.asyncio
    async def test_articles_admin_works_when_blog_enabled(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_enabled: list[FeatureFlag],
    ) -> None:
        """GET /admin/articles should return 200 when blog_module is enabled."""
        response = await authenticated_client.get("/api/v1/admin/articles")
        assert response.status_code == 200


@pytest.mark.integration
class TestFeatureFlagCasesModule:
    """T2-03: Cases module admin routes."""

    @pytest.mark.asyncio
    async def test_cases_admin_blocked_when_disabled(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        response = await authenticated_client.get("/api/v1/admin/cases")
        assert response.status_code == 403
        data = response.json()["detail"]
        assert data["feature"] == "cases_module"


@pytest.mark.integration
class TestFeatureFlagReviewsModule:
    """T2-04: Reviews module admin routes."""

    @pytest.mark.asyncio
    async def test_reviews_admin_blocked_when_disabled(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        response = await authenticated_client.get("/api/v1/admin/reviews")
        assert response.status_code == 403
        data = response.json()["detail"]
        assert data["feature"] == "reviews_module"


@pytest.mark.integration
class TestFeatureFlagFAQModule:
    """T2-05: FAQ module admin routes."""

    @pytest.mark.asyncio
    async def test_faq_admin_blocked_when_disabled(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        response = await authenticated_client.get("/api/v1/admin/faq")
        assert response.status_code == 403
        data = response.json()["detail"]
        assert data["feature"] == "faq_module"


@pytest.mark.integration
class TestFeatureFlagTeamModule:
    """T2-06: Team/employees module admin routes."""

    @pytest.mark.asyncio
    async def test_employees_admin_blocked_when_disabled(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        response = await authenticated_client.get("/api/v1/admin/employees")
        assert response.status_code == 403
        data = response.json()["detail"]
        assert data["feature"] == "team_module"


@pytest.mark.integration
class TestFeatureFlagBulkRouter:
    """T2-07, T2-08: Bulk operations with feature flag check."""

    @pytest.mark.asyncio
    async def test_bulk_op_blocked_for_disabled_resource(
        self,
        authenticated_client: AsyncClient,
        feature_flags_mixed: list[FeatureFlag],
    ) -> None:
        """Bulk op for reviews (disabled in mixed flags) should return 403."""
        response = await authenticated_client.post(
            "/api/v1/admin/bulk",
            json={"resource_type": "reviews", "action": "publish", "ids": [str(uuid4())]},
        )
        assert response.status_code == 403
        data = response.json()["detail"]
        assert data["feature"] == "reviews_module"


@pytest.mark.integration
class TestFeatureFlagSuperuserBypass:
    """T2-10, T2-11: Superuser and platform owner bypass feature flags."""

    @pytest.mark.asyncio
    async def test_superuser_bypasses_feature_flag(
        self,
        superuser_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        """Superuser should access articles even when blog_module is disabled."""
        response = await superuser_client.get("/api/v1/admin/articles")
        # Superuser bypasses feature check via PermissionChecker (is_superuser=True)
        assert response.status_code == 200


@pytest.mark.integration
class TestFeatureFlagErrorMessage:
    """T2-12: Error message validation."""

    @pytest.mark.asyncio
    async def test_error_message_is_user_friendly(
        self,
        authenticated_client: AsyncClient,
        feature_flags_all_disabled: list[FeatureFlag],
    ) -> None:
        """403 feature_disabled message should be user-friendly."""
        response = await authenticated_client.get("/api/v1/admin/articles")
        assert response.status_code == 403
        detail = response.json()["detail"]["detail"]
        assert "not available for your organization" in detail
        assert "Contact your administrator" in detail
