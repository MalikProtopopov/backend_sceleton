"""API tests: RBAC permission enforcement across endpoints."""

import pytest
from httpx import AsyncClient

from tests.helpers import assert_error_response


@pytest.mark.api
@pytest.mark.asyncio
class TestRBACEnforcement:

    async def test_editor_cannot_delete_article(
        self, editor_client: AsyncClient, tenant_active, db_session
    ):
        """Editor has articles:read/create/update but NOT articles:delete."""
        from uuid import uuid4
        fake_id = uuid4()
        resp = await editor_client.delete(
            f"/api/v1/admin/articles/{fake_id}",
        )
        # Should be 403 permission_denied (no articles:delete permission)
        assert_error_response(resp, 403, "permission_denied", {"restriction_level": "user"})

    async def test_content_manager_cannot_create_case(
        self, cm_client: AsyncClient, tenant_active
    ):
        """Content manager has no cases:create permission."""
        resp = await cm_client.post(
            "/api/v1/admin/cases",
            json={
                "client_name": "Test",
                "project_year": 2024,
            },
        )
        assert_error_response(resp, 403, "permission_denied", {"restriction_level": "user"})

    async def test_editor_cannot_manage_users(
        self, editor_client: AsyncClient
    ):
        """Editor has no users:read permission."""
        resp = await editor_client.get("/api/v1/auth/users")
        assert_error_response(resp, 403, "permission_denied")

    async def test_platform_owner_can_list_articles(
        self, platform_owner_client: AsyncClient
    ):
        """Platform owner (superuser) can list articles."""
        resp = await platform_owner_client.get("/api/v1/admin/articles")
        assert resp.status_code == 200

    async def test_unauthenticated_admin_returns_401(
        self, client: AsyncClient
    ):
        resp = await client.get("/api/v1/admin/articles")
        assert resp.status_code == 401
