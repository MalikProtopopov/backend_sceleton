"""Multi-tenant test fixtures.

Provides tenants with different states, users with real role names,
and tenants with specific feature flags disabled.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.auth.models import AdminUser, Role
from app.modules.tenants.models import AVAILABLE_FEATURES, FeatureFlag, Tenant

TEST_PASSWORD = "testpass123"


# ============================================================================
# Tenant Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def tenant_active(db_session: AsyncSession) -> Tenant:
    """Active tenant with all feature flags enabled."""
    uid = uuid4()
    tenant = Tenant(
        id=uid,
        slug=f"active-{uid.hex[:8]}",
        name="Active Corp",
        domain=f"active-{uid.hex[:8]}.test",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    # Create all feature flags enabled
    for fname in AVAILABLE_FEATURES:
        flag = FeatureFlag(
            tenant_id=tenant.id,
            feature_name=fname,
            enabled=True,
            description=f"Flag {fname}",
        )
        db_session.add(flag)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_inactive(db_session: AsyncSession) -> Tenant:
    """Inactive (suspended) tenant."""
    uid = uuid4()
    tenant = Tenant(
        id=uid,
        slug=f"inactive-{uid.hex[:8]}",
        name="Inactive Corp",
        domain=f"inactive-{uid.hex[:8]}.test",
        is_active=False,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_deleted(db_session: AsyncSession) -> Tenant:
    """Soft-deleted tenant."""
    uid = uuid4()
    tenant = Tenant(
        id=uid,
        slug=f"deleted-{uid.hex[:8]}",
        name="Deleted Corp",
        domain=f"deleted-{uid.hex[:8]}.test",
        is_active=True,
        deleted_at=datetime.now(UTC),
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def second_tenant(db_session: AsyncSession) -> Tenant:
    """Second active tenant for cross-tenant tests."""
    uid = uuid4()
    tenant = Tenant(
        id=uid,
        slug=f"second-{uid.hex[:8]}",
        name="Second Corp",
        domain=f"second-{uid.hex[:8]}.test",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    for fname in AVAILABLE_FEATURES:
        flag = FeatureFlag(
            tenant_id=tenant.id,
            feature_name=fname,
            enabled=True,
            description=f"Flag {fname}",
        )
        db_session.add(flag)
    await db_session.flush()
    return tenant


def _make_disabled_tenant_fixture(disabled_feature: str):
    """Factory to create tenant fixtures with a specific feature disabled."""

    @pytest_asyncio.fixture
    async def _fixture(db_session: AsyncSession) -> Tenant:
        uid = uuid4()
        tenant = Tenant(
            id=uid,
            slug=f"no-{disabled_feature[:8]}-{uid.hex[:8]}",
            name=f"No {disabled_feature} Corp",
            domain=f"no-{disabled_feature[:8]}-{uid.hex[:8]}.test",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()
        for fname in AVAILABLE_FEATURES:
            flag = FeatureFlag(
                tenant_id=tenant.id,
                feature_name=fname,
                enabled=(fname != disabled_feature),
                description=f"Flag {fname}",
            )
            db_session.add(flag)
        await db_session.flush()
        return tenant

    return _fixture


tenant_blog_disabled = _make_disabled_tenant_fixture("blog_module")
tenant_cases_disabled = _make_disabled_tenant_fixture("cases_module")
tenant_reviews_disabled = _make_disabled_tenant_fixture("reviews_module")
tenant_faq_disabled = _make_disabled_tenant_fixture("faq_module")
tenant_team_disabled = _make_disabled_tenant_fixture("team_module")
tenant_services_disabled = _make_disabled_tenant_fixture("services_module")
tenant_seo_disabled = _make_disabled_tenant_fixture("seo_advanced")


# ============================================================================
# Role + User Helpers
# ============================================================================


async def _create_role(
    db_session: AsyncSession, tenant_id, name: str, is_system: bool = True
) -> Role:
    role = Role(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        description=f"System role: {name}",
        is_system=is_system,
    )
    db_session.add(role)
    await db_session.flush()
    return role


async def _create_user(
    db_session: AsyncSession,
    tenant_id,
    role: Role,
    *,
    is_superuser: bool = False,
    prefix: str = "",
) -> AdminUser:
    uid = uuid4()
    user = AdminUser(
        id=uid,
        tenant_id=tenant_id,
        email=f"{prefix or role.name}-{uid.hex[:8]}@test.local",
        password_hash=hash_password(TEST_PASSWORD),
        first_name=prefix.title() or role.name.replace("_", " ").title(),
        last_name="Testov",
        role_id=role.id,
        is_active=True,
        is_superuser=is_superuser,
    )
    db_session.add(user)
    await db_session.flush()
    return user


def _make_token(user: AdminUser, tenant: Tenant, permissions: list[str]) -> str:
    return create_access_token(
        {
            "sub": str(user.id),
            "tenant_id": str(tenant.id),
            "email": user.email,
            "role": user.role.name if user.role else None,
            "permissions": permissions,
            "is_superuser": user.is_superuser,
        },
        expires_delta=timedelta(hours=1),
    )


async def _make_client(
    app: FastAPI, token: str
) -> AsyncGenerator[AsyncClient, None]:
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    ) as ac:
        yield ac


# ============================================================================
# Platform Owner
# ============================================================================


@pytest_asyncio.fixture
async def platform_owner_role(
    db_session: AsyncSession, tenant_active: Tenant
) -> Role:
    return await _create_role(db_session, tenant_active.id, "platform_owner")


@pytest_asyncio.fixture
async def platform_owner_user(
    db_session: AsyncSession, tenant_active: Tenant, platform_owner_role: Role
) -> AdminUser:
    return await _create_user(
        db_session, tenant_active.id, platform_owner_role, is_superuser=True
    )


@pytest.fixture
def platform_owner_token(
    platform_owner_user: AdminUser, tenant_active: Tenant
) -> str:
    return _make_token(platform_owner_user, tenant_active, ["*"])


@pytest_asyncio.fixture
async def platform_owner_client(
    app: FastAPI, platform_owner_token: str
) -> AsyncGenerator[AsyncClient, None]:
    async for c in _make_client(app, platform_owner_token):
        yield c


# ============================================================================
# Site Owner
# ============================================================================


@pytest_asyncio.fixture
async def site_owner_role(
    db_session: AsyncSession, tenant_active: Tenant
) -> Role:
    return await _create_role(db_session, tenant_active.id, "site_owner")


@pytest_asyncio.fixture
async def site_owner_user(
    db_session: AsyncSession, tenant_active: Tenant, site_owner_role: Role
) -> AdminUser:
    return await _create_user(db_session, tenant_active.id, site_owner_role)


@pytest.fixture
def site_owner_token(site_owner_user: AdminUser, tenant_active: Tenant) -> str:
    return _make_token(
        site_owner_user,
        tenant_active,
        [
            "articles:read", "articles:create", "articles:update", "articles:delete", "articles:publish",
            "cases:read", "cases:create", "cases:update", "cases:delete", "cases:publish",
            "reviews:read", "reviews:create", "reviews:update", "reviews:delete",
            "faq:read", "faq:create", "faq:update", "faq:delete",
            "services:read", "services:create", "services:update", "services:delete",
            "employees:read", "employees:create", "employees:update", "employees:delete",
            "inquiries:read", "inquiries:update", "inquiries:delete",
            "seo:read", "seo:update",
            "settings:read", "settings:update",
            "users:read", "users:create", "users:update", "users:delete", "users:manage",
            "audit:read",
        ],
    )


@pytest_asyncio.fixture
async def site_owner_client(
    app: FastAPI, site_owner_token: str
) -> AsyncGenerator[AsyncClient, None]:
    async for c in _make_client(app, site_owner_token):
        yield c


# ============================================================================
# Content Manager
# ============================================================================


@pytest_asyncio.fixture
async def cm_role(db_session: AsyncSession, tenant_active: Tenant) -> Role:
    return await _create_role(db_session, tenant_active.id, "content_manager")


@pytest_asyncio.fixture
async def cm_user(
    db_session: AsyncSession, tenant_active: Tenant, cm_role: Role
) -> AdminUser:
    return await _create_user(
        db_session, tenant_active.id, cm_role, prefix="cm"
    )


@pytest.fixture
def cm_token(cm_user: AdminUser, tenant_active: Tenant) -> str:
    return _make_token(
        cm_user,
        tenant_active,
        [
            "articles:read", "articles:create", "articles:update",
            "faq:read", "faq:create", "faq:update",
            "services:read", "services:update",
            "employees:read",
        ],
    )


@pytest_asyncio.fixture
async def cm_client(
    app: FastAPI, cm_token: str
) -> AsyncGenerator[AsyncClient, None]:
    async for c in _make_client(app, cm_token):
        yield c


# ============================================================================
# Editor (most restricted)
# ============================================================================


@pytest_asyncio.fixture
async def editor_role(db_session: AsyncSession, tenant_active: Tenant) -> Role:
    return await _create_role(db_session, tenant_active.id, "editor")


@pytest_asyncio.fixture
async def editor_user(
    db_session: AsyncSession, tenant_active: Tenant, editor_role: Role
) -> AdminUser:
    return await _create_user(
        db_session, tenant_active.id, editor_role, prefix="editor"
    )


@pytest.fixture
def editor_token(editor_user: AdminUser, tenant_active: Tenant) -> str:
    return _make_token(
        editor_user,
        tenant_active,
        ["articles:read", "articles:create", "articles:update", "faq:read", "faq:create", "faq:update"],
    )


@pytest_asyncio.fixture
async def editor_client(
    app: FastAPI, editor_token: str
) -> AsyncGenerator[AsyncClient, None]:
    async for c in _make_client(app, editor_token):
        yield c


# ============================================================================
# Second-tenant user (for cross-tenant tests)
# ============================================================================


@pytest_asyncio.fixture
async def second_tenant_role(
    db_session: AsyncSession, second_tenant: Tenant
) -> Role:
    return await _create_role(db_session, second_tenant.id, "site_owner")


@pytest_asyncio.fixture
async def second_tenant_user(
    db_session: AsyncSession, second_tenant: Tenant, second_tenant_role: Role
) -> AdminUser:
    return await _create_user(
        db_session, second_tenant.id, second_tenant_role, prefix="second"
    )
