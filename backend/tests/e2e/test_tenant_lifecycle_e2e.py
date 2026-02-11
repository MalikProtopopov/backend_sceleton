"""E2E: Tenant lifecycle -- create -> add user -> login -> use features -> deactivate -> blocked."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.auth.models import AdminUser, Role
from app.modules.tenants.models import AVAILABLE_FEATURES, FeatureFlag, Tenant


@pytest.mark.e2e
@pytest.mark.asyncio
class TestTenantLifecycleE2E:

    async def test_full_lifecycle(self, client: AsyncClient, db_session: AsyncSession):
        """Create tenant, create user, login, access data, deactivate, verify blocked."""

        # Step 1: Create tenant directly in DB
        uid = uuid4()
        tenant = Tenant(
            id=uid,
            slug=f"e2e-{uid.hex[:8]}",
            name="E2E Corp",
            domain=f"e2e-{uid.hex[:8]}.example.com",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()

        # Create feature flags
        for fname in AVAILABLE_FEATURES:
            db_session.add(
                FeatureFlag(
                    tenant_id=tenant.id,
                    feature_name=fname,
                    enabled=True,
                    description=f"E2E {fname}",
                )
            )
        await db_session.flush()

        # Step 2: Create role and user
        role = Role(
            id=uuid4(),
            tenant_id=tenant.id,
            name=f"admin-e2e-{uuid4().hex[:6]}",
            description="E2E admin",
        )
        db_session.add(role)
        await db_session.flush()

        password = "E2ePassword123!"
        user_email = f"e2e-{uuid4().hex[:8]}@example.com"
        user = AdminUser(
            id=uuid4(),
            tenant_id=tenant.id,
            email=user_email,
            password_hash=hash_password(password),
            first_name="E2E",
            last_name="User",
            role_id=role.id,
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        await db_session.flush()

        # Step 3: Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": password},
            headers={"X-Tenant-ID": str(tenant.id)},
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        login_data = login_resp.json()
        access_token = login_data["tokens"]["access_token"]
        assert access_token is not None

        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Step 4: Access public articles (should work)
        articles_resp = await client.get(
            "/api/v1/public/articles",
            params={"tenant_id": str(tenant.id), "locale": "ru"},
        )
        assert articles_resp.status_code == 200

        # Step 5: Deactivate tenant
        tenant.is_active = False
        await db_session.flush()

        # Step 6: Next authenticated request should fail
        blocked_resp = await client.get(
            "/api/v1/admin/articles",
            headers=auth_headers,
        )
        assert blocked_resp.status_code == 403
