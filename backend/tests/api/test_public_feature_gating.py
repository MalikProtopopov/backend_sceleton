"""API tests: public routes return 404 when feature is disabled."""

import pytest
from httpx import AsyncClient

from tests.helpers import assert_error_response


@pytest.mark.api
@pytest.mark.asyncio
class TestPublicFeatureGating:
    """Test that disabled features return 404 feature_not_available on public routes."""

    async def test_public_articles_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_blog_disabled
    ):
        resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(tenant_blog_disabled.id), "locale": "ru"},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "blog_module"})

    async def test_public_topics_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_blog_disabled
    ):
        resp = await client.get(
            "/api/v1/public/topics",
            params={"tenant_id": str(tenant_blog_disabled.id), "locale": "ru"},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "blog_module"})

    async def test_public_cases_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_cases_disabled
    ):
        resp = await client.get(
            "/api/v1/public/cases",
            params={"tenant_id": str(tenant_cases_disabled.id), "locale": "ru"},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "cases_module"})

    async def test_public_reviews_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_reviews_disabled
    ):
        resp = await client.get(
            "/api/v1/public/reviews",
            params={"tenant_id": str(tenant_reviews_disabled.id)},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "reviews_module"})

    async def test_public_faq_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_faq_disabled
    ):
        resp = await client.get(
            "/api/v1/public/faq",
            params={"tenant_id": str(tenant_faq_disabled.id), "locale": "ru"},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "faq_module"})

    async def test_public_employees_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_team_disabled
    ):
        resp = await client.get(
            "/api/v1/public/employees",
            params={"tenant_id": str(tenant_team_disabled.id), "locale": "ru"},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "team_module"})

    async def test_public_services_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_services_disabled
    ):
        resp = await client.get(
            "/api/v1/public/services",
            params={"tenant_id": str(tenant_services_disabled.id), "locale": "ru"},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "services_module"})

    async def test_public_sitemap_available_when_seo_disabled(
        self, client: AsyncClient, tenant_seo_disabled
    ):
        """Public sitemap/robots should NOT be gated by seo_advanced."""
        resp = await client.get(
            "/api/v1/public/sitemap.xml",
            params={"tenant_id": str(tenant_seo_disabled.id)},
        )
        # Should succeed (200) or return content, NOT 404 feature_not_available
        assert resp.status_code != 404 or "feature_not_available" not in resp.text

    async def test_public_robots_available_when_seo_disabled(
        self, client: AsyncClient, tenant_seo_disabled
    ):
        resp = await client.get(
            "/api/v1/public/robots.txt",
            params={"tenant_id": str(tenant_seo_disabled.id)},
        )
        assert resp.status_code != 404 or "feature_not_available" not in resp.text

    async def test_public_products_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_catalog_disabled
    ):
        resp = await client.get(
            "/api/v1/public/products",
            params={"tenant_id": str(tenant_catalog_disabled.id)},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "catalog_module"})

    async def test_public_products_feature_enabled_returns_200(
        self, client: AsyncClient, tenant_active
    ):
        resp = await client.get(
            "/api/v1/public/products",
            params={"tenant_id": str(tenant_active.id)},
        )
        assert resp.status_code == 200

    async def test_public_categories_feature_disabled_returns_404(
        self, client: AsyncClient, tenant_catalog_disabled
    ):
        resp = await client.get(
            "/api/v1/public/categories",
            params={"tenant_id": str(tenant_catalog_disabled.id)},
        )
        assert_error_response(resp, 404, "feature_not_available", {"feature": "catalog_module"})

    async def test_feature_not_available_has_hint_field(
        self, client: AsyncClient, tenant_blog_disabled
    ):
        resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(tenant_blog_disabled.id), "locale": "ru"},
        )
        body = resp.json()
        detail = body if "type" in body else body.get("detail", body)
        assert "_hint" in detail
