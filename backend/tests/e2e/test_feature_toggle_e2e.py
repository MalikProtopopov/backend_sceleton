"""E2E: Feature toggle -- enable blog -> verify -> disable blog -> verify 404."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenants.models import AVAILABLE_FEATURES, FeatureFlag, Tenant
from tests.helpers import set_feature_flag


@pytest.mark.e2e
@pytest.mark.asyncio
class TestFeatureToggleE2E:

    async def test_toggle_blog_module(self, client: AsyncClient, db_session: AsyncSession):
        """Enable blog -> public articles works -> disable blog -> public articles 404."""

        # Setup: create tenant with blog enabled
        uid = uuid4()
        tenant = Tenant(
            id=uid,
            slug=f"toggle-{uid.hex[:8]}",
            name="Toggle Corp",
            domain=f"toggle-{uid.hex[:8]}.test",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()
        for fname in AVAILABLE_FEATURES:
            db_session.add(
                FeatureFlag(
                    tenant_id=tenant.id,
                    feature_name=fname,
                    enabled=True,
                    description=f"Toggle {fname}",
                )
            )
        await db_session.flush()

        # Blog enabled -> should work
        resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(tenant.id), "locale": "ru"},
        )
        assert resp.status_code == 200

        # Disable blog
        await set_feature_flag(db_session, tenant.id, "blog_module", False)

        # Blog disabled -> should return 404 feature_not_available
        resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(tenant.id), "locale": "ru"},
        )
        assert resp.status_code == 404
        body = resp.json()
        detail = body if "type" in body else body.get("detail", body)
        assert detail.get("type", "").endswith("/feature_not_available")
