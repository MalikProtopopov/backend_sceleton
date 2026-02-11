"""Multi-tenant test fixtures for security, isolation, and feature flag testing.

Provides a complete set of tenants, roles, users, feature flags, and auth
tokens needed by integration, security, and E2E tests.

Usage:
    Import fixtures via pytest_plugins in conftest.py or use directly.
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.modules.auth.models import AdminUser, AuditLog, Role
from app.modules.tenants.models import FeatureFlag, Tenant

TEST_PASSWORD = "testpass123"


# ============================================================================
# Tenants
# ============================================================================


@pytest_asyncio.fixture
async def inactive_tenant(db_session: AsyncSession) -> Tenant:
    """Tenant with is_active=False (suspended)."""
    uid = uuid4()
    tenant = Tenant(
        id=uid,
        slug=f"inactive-{uid.hex[:8]}",
        name="Inactive Corp",
        domain=f"inactive-{uid.hex[:8]}.example.com",
        is_active=False,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def deleted_tenant(db_session: AsyncSession) -> Tenant:
    """Soft-deleted tenant (deleted_at set)."""
    uid = uuid4()
    tenant = Tenant(
        id=uid,
        slug=f"deleted-{uid.hex[:8]}",
        name="Deleted Corp",
        domain=f"deleted-{uid.hex[:8]}.example.com",
        is_active=True,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


@pytest_asyncio.fixture
async def tenant_b(db_session: AsyncSession) -> Tenant:
    """Second active tenant for cross-tenant isolation tests."""
    uid = uuid4()
    tenant = Tenant(
        id=uid,
        slug=f"tenant-b-{uid.hex[:8]}",
        name="Tenant B Corp",
        domain=f"tenant-b-{uid.hex[:8]}.example.com",
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.flush()
    return tenant


# ============================================================================
# Roles
# ============================================================================


@pytest_asyncio.fixture
async def platform_owner_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """Platform owner role with platform:* permissions."""
    role = Role(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="platform_owner",
        description="Platform owner with full platform access",
        is_system=True,
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def site_owner_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """Site owner role with wildcard permissions within own tenant."""
    role = Role(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="site_owner",
        description="Site owner with full tenant access",
        is_system=True,
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def editor_role(db_session: AsyncSession, test_tenant: Tenant) -> Role:
    """Editor role with limited content permissions."""
    role = Role(
        id=uuid4(),
        tenant_id=test_tenant.id,
        name="editor",
        description="Content editor",
    )
    db_session.add(role)
    await db_session.flush()
    return role


@pytest_asyncio.fixture
async def tenant_b_role(db_session: AsyncSession, tenant_b: Tenant) -> Role:
    """Admin role in tenant_b for isolation tests."""
    role = Role(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name=f"admin-b-{uuid4().hex[:8]}",
        description="Admin role in tenant B",
    )
    db_session.add(role)
    await db_session.flush()
    return role


# ============================================================================
# Users
# ============================================================================


@pytest_asyncio.fixture
async def platform_owner_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    platform_owner_role: Role,
) -> AdminUser:
    """Platform owner user in the active tenant."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"platform-owner-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="Platform",
        last_name="Owner",
        role_id=platform_owner_role.id,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def site_owner_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    site_owner_role: Role,
) -> AdminUser:
    """Site owner user."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"site-owner-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="Site",
        last_name="Owner",
        role_id=site_owner_role.id,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def editor_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    editor_role: Role,
) -> AdminUser:
    """Editor user with limited permissions."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"editor-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="Editor",
        last_name="User",
        role_id=editor_role.id,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def inactive_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_role: Role,
) -> AdminUser:
    """Inactive user (is_active=False)."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"inactive-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="Inactive",
        last_name="User",
        role_id=test_role.id,
        is_active=False,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def deleted_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_role: Role,
) -> AdminUser:
    """Soft-deleted user."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"deleted-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="Deleted",
        last_name="User",
        role_id=test_role.id,
        is_active=True,
        is_superuser=False,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def inactive_tenant_user(
    db_session: AsyncSession,
    inactive_tenant: Tenant,
) -> AdminUser:
    """Active user belonging to an inactive tenant."""
    # Create a role in the inactive tenant
    role = Role(
        id=uuid4(),
        tenant_id=inactive_tenant.id,
        name=f"admin-{uuid4().hex[:8]}",
        description="Admin in inactive tenant",
    )
    db_session.add(role)
    await db_session.flush()

    user = AdminUser(
        id=uuid4(),
        tenant_id=inactive_tenant.id,
        email=f"user-inactive-tenant-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="InactiveTenant",
        last_name="User",
        role_id=role.id,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def tenant_b_user(
    db_session: AsyncSession,
    tenant_b: Tenant,
    tenant_b_role: Role,
) -> AdminUser:
    """User in tenant_b for cross-tenant tests."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=tenant_b.id,
        email=f"user-b-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="TenantB",
        last_name="User",
        role_id=tenant_b_role.id,
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def force_pwd_user(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_role: Role,
) -> AdminUser:
    """User with force_password_change=True."""
    user = AdminUser(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email=f"force-pwd-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password(TEST_PASSWORD),
        first_name="ForcePwd",
        last_name="User",
        role_id=test_role.id,
        is_active=True,
        is_superuser=False,
        force_password_change=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ============================================================================
# Feature Flags
# ============================================================================


@pytest_asyncio.fixture
async def feature_flags_mixed(db_session: AsyncSession, test_tenant: Tenant) -> list[FeatureFlag]:
    """Create feature flags: blog=True, cases=True, reviews=False, faq=True, team=False."""
    config = {
        "blog_module": True,
        "cases_module": True,
        "reviews_module": False,
        "faq_module": True,
        "team_module": False,
        "seo_advanced": True,
        "multilang": False,
        "analytics_advanced": False,
    }
    flags = []
    for name, enabled in config.items():
        flag = FeatureFlag(tenant_id=test_tenant.id, feature_name=name, enabled=enabled)
        db_session.add(flag)
        flags.append(flag)
    await db_session.flush()
    return flags


@pytest_asyncio.fixture
async def feature_flags_all_enabled(db_session: AsyncSession, test_tenant: Tenant) -> list[FeatureFlag]:
    """All feature flags enabled for the test tenant."""
    names = [
        "blog_module", "cases_module", "reviews_module", "faq_module",
        "team_module", "seo_advanced", "multilang", "analytics_advanced",
    ]
    flags = []
    for name in names:
        flag = FeatureFlag(tenant_id=test_tenant.id, feature_name=name, enabled=True)
        db_session.add(flag)
        flags.append(flag)
    await db_session.flush()
    return flags


@pytest_asyncio.fixture
async def feature_flags_all_disabled(db_session: AsyncSession, test_tenant: Tenant) -> list[FeatureFlag]:
    """All feature flags disabled for the test tenant."""
    names = [
        "blog_module", "cases_module", "reviews_module", "faq_module",
        "team_module", "seo_advanced", "multilang", "analytics_advanced",
    ]
    flags = []
    for name in names:
        flag = FeatureFlag(tenant_id=test_tenant.id, feature_name=name, enabled=False)
        db_session.add(flag)
        flags.append(flag)
    await db_session.flush()
    return flags


@pytest_asyncio.fixture
async def feature_flags_tenant_b(db_session: AsyncSession, tenant_b: Tenant) -> list[FeatureFlag]:
    """Feature flags for tenant_b: blog=True, cases=False."""
    config = {"blog_module": True, "cases_module": False}
    flags = []
    for name, enabled in config.items():
        flag = FeatureFlag(tenant_id=tenant_b.id, feature_name=name, enabled=enabled)
        db_session.add(flag)
        flags.append(flag)
    await db_session.flush()
    return flags


# ============================================================================
# Auth Tokens and Clients
# ============================================================================


def _make_token(user: AdminUser, tenant: Tenant, role_name: str, permissions: list[str]) -> str:
    """Helper to create a JWT token for a user."""
    token_data = {
        "sub": str(user.id),
        "tenant_id": str(tenant.id),
        "email": user.email,
        "role": role_name,
        "permissions": permissions,
        "is_superuser": user.is_superuser,
    }
    return create_access_token(token_data, expires_delta=timedelta(hours=1))


@pytest.fixture
def platform_owner_token(platform_owner_user: AdminUser, test_tenant: Tenant) -> str:
    return _make_token(platform_owner_user, test_tenant, "platform_owner", ["*"])


@pytest.fixture
def platform_owner_headers(platform_owner_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {platform_owner_token}"}


@pytest_asyncio.fixture
async def platform_owner_client(
    app: FastAPI, platform_owner_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=platform_owner_headers,
    ) as ac:
        yield ac


@pytest.fixture
def site_owner_token(site_owner_user: AdminUser, test_tenant: Tenant) -> str:
    return _make_token(site_owner_user, test_tenant, "site_owner", ["*"])


@pytest.fixture
def site_owner_headers(site_owner_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {site_owner_token}"}


@pytest_asyncio.fixture
async def site_owner_client(
    app: FastAPI, site_owner_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=site_owner_headers,
    ) as ac:
        yield ac


@pytest.fixture
def editor_token(editor_user: AdminUser, test_tenant: Tenant) -> str:
    return _make_token(
        editor_user, test_tenant, "editor",
        ["articles:read", "articles:create", "articles:update"],
    )


@pytest.fixture
def editor_headers(editor_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {editor_token}"}


@pytest_asyncio.fixture
async def editor_client(
    app: FastAPI, editor_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=editor_headers,
    ) as ac:
        yield ac


@pytest.fixture
def inactive_tenant_token(inactive_tenant_user: AdminUser, inactive_tenant: Tenant) -> str:
    """Valid JWT token for a user in an inactive tenant."""
    return _make_token(
        inactive_tenant_user, inactive_tenant, "admin", ["*"],
    )


@pytest.fixture
def inactive_tenant_headers(inactive_tenant_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {inactive_tenant_token}"}


@pytest_asyncio.fixture
async def inactive_tenant_client(
    app: FastAPI, inactive_tenant_headers: dict[str, str],
) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=inactive_tenant_headers,
    ) as ac:
        yield ac


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock EmailService to capture email sends."""
    mock_welcome = AsyncMock(return_value=True)
    mock_reset = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.modules.notifications.service.EmailService.send_welcome_email",
        mock_welcome,
    )
    monkeypatch.setattr(
        "app.modules.notifications.service.EmailService.send_password_reset_email",
        mock_reset,
    )
    return {"welcome": mock_welcome, "reset": mock_reset}


@pytest_asyncio.fixture
async def audit_log_count(db_session: AsyncSession, test_tenant: Tenant) -> int:
    """Return current audit log count for delta assertions."""
    result = await db_session.execute(
        select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == test_tenant.id)
    )
    return result.scalar() or 0
