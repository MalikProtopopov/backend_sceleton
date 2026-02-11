"""API tests: admin routes return 403 feature_disabled when module is off."""

import pytest
from httpx import AsyncClient

from tests.helpers import assert_error_response, set_feature_flag


@pytest.mark.api
@pytest.mark.asyncio
class TestAdminFeatureGating:
    """Disable a feature on tenant_active and verify admin routes return 403.

    The site_owner_client is authenticated for tenant_active (all features
    enabled by default).  Each test disables a single feature via
    set_feature_flag and then asserts the matching admin route returns 403.
    """

    async def test_admin_articles_disabled(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "blog_module", False)
        resp = await site_owner_client.get("/api/v1/admin/articles")
        assert_error_response(
            resp, 403, "feature_disabled",
            {"restriction_level": "organization", "feature": "blog_module"},
        )

    async def test_admin_cases_disabled(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "cases_module", False)
        resp = await site_owner_client.get("/api/v1/admin/cases")
        assert_error_response(
            resp, 403, "feature_disabled",
            {"restriction_level": "organization", "feature": "cases_module"},
        )

    async def test_admin_reviews_disabled(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "reviews_module", False)
        resp = await site_owner_client.get("/api/v1/admin/reviews")
        assert_error_response(
            resp, 403, "feature_disabled",
            {"restriction_level": "organization", "feature": "reviews_module"},
        )

    async def test_admin_faq_disabled(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "faq_module", False)
        resp = await site_owner_client.get("/api/v1/admin/faq")
        assert_error_response(
            resp, 403, "feature_disabled",
            {"restriction_level": "organization", "feature": "faq_module"},
        )

    async def test_admin_employees_disabled(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "team_module", False)
        resp = await site_owner_client.get("/api/v1/admin/employees")
        assert_error_response(
            resp, 403, "feature_disabled",
            {"restriction_level": "organization", "feature": "team_module"},
        )

    async def test_admin_services_disabled(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "services_module", False)
        resp = await site_owner_client.get("/api/v1/admin/services")
        assert_error_response(
            resp, 403, "feature_disabled",
            {"restriction_level": "organization", "feature": "services_module"},
        )

    async def test_admin_seo_disabled(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "seo_advanced", False)
        resp = await site_owner_client.get("/api/v1/admin/seo/routes")
        assert_error_response(
            resp, 403, "feature_disabled",
            {"restriction_level": "organization", "feature": "seo_advanced"},
        )

    async def test_superuser_bypasses_disabled_feature(
        self, superuser_client: AsyncClient, test_tenant, db_session
    ):
        """Superuser should still access disabled modules.

        Note: superuser_client is authenticated for test_tenant (from conftest),
        not tenant_active.  We explicitly disable the flag on test_tenant and
        verify the superuser bypasses the check.
        """
        await set_feature_flag(db_session, test_tenant.id, "blog_module", False)
        resp = await superuser_client.get("/api/v1/admin/articles")
        assert resp.status_code != 403

    async def test_feature_disabled_error_has_contact_admin(
        self, site_owner_client: AsyncClient, tenant_active, db_session
    ):
        await set_feature_flag(db_session, tenant_active.id, "blog_module", False)
        resp = await site_owner_client.get("/api/v1/admin/articles")
        body = assert_error_response(resp, 403, "feature_disabled")
        assert body["contact_admin"] is True
        assert body["restriction_level"] == "organization"
