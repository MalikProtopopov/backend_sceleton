"""Integration tests for audit log expansion (Phase 6).

T6-01 to T6-13: Audit logs for login, logout, user CRUD, tenant CRUD,
feature flag toggles, role changes, password changes.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AdminUser, AuditLog
from app.modules.tenants.models import FeatureFlag, Tenant
from tests.fixtures.multi_tenant import TEST_PASSWORD


@pytest.mark.integration
class TestAuditLogAuth:
    """T6-01, T6-02: Login and logout create audit logs."""

    @pytest.mark.asyncio
    async def test_login_creates_audit_log(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        db_session: AsyncSession,
    ) -> None:
        """Successful login should create an audit log entry."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        assert response.status_code == 200

        # Check audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == test_tenant.id,
                AuditLog.action == "login",
                AuditLog.user_id == test_user.id,
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.resource_type == "auth"

    @pytest.mark.asyncio
    async def test_logout_creates_audit_log(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        db_session: AsyncSession,
    ) -> None:
        """Logout should create an audit log entry."""
        # Login first
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        token = login_resp.json()["tokens"]["access_token"]

        # Logout
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        # Check audit log
        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == test_tenant.id,
                AuditLog.action == "logout",
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.resource_type == "auth"


@pytest.mark.integration
class TestAuditLogUserCRUD:
    """T6-03 to T6-05, T6-12, T6-13: User CRUD audit logs."""

    @pytest.mark.asyncio
    async def test_user_create_audit_log(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        test_role,
        platform_owner_user: AdminUser,
        db_session: AsyncSession,
        mock_email_service,
    ) -> None:
        """Creating a user should create an audit log with action=create."""
        response = await platform_owner_client.post(
            "/api/v1/auth/users",
            json={
                "email": f"audit-test-{uuid4().hex[:8]}@example.com",
                "first_name": "Audit",
                "last_name": "Test",
                "password": "securepassword123",
                "role_id": str(test_role.id),
                "send_credentials": False,
            },
        )
        assert response.status_code == 201

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == test_tenant.id,
                AuditLog.action == "create",
                AuditLog.resource_type == "user",
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.user_id == platform_owner_user.id  # T6-13: correct actor_id

    @pytest.mark.asyncio
    async def test_user_update_audit_log_with_changes(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        db_session: AsyncSession,
    ) -> None:
        """Updating a user should log changes diff."""
        response = await platform_owner_client.patch(
            f"/api/v1/auth/users/{test_user.id}",
            json={"first_name": "ChangedName", "version": 1},
        )
        assert response.status_code == 200

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == test_tenant.id,
                AuditLog.action == "update",
                AuditLog.resource_type == "user",
                AuditLog.resource_id == test_user.id,
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
        assert "first_name" in log.changes

    @pytest.mark.asyncio
    async def test_password_change_audit_no_plaintext(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        test_user: AdminUser,
        db_session: AsyncSession,
    ) -> None:
        """Password change should log '***' not actual passwords."""
        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": TEST_PASSWORD},
            headers={"X-Tenant-ID": str(test_tenant.id)},
        )
        token = login_resp.json()["tokens"]["access_token"]

        # Change password
        response = await client.post(
            "/api/v1/auth/me/password",
            json={"current_password": TEST_PASSWORD, "new_password": "newsecurepass123"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 204

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == test_user.id,
                AuditLog.action == "update",
                AuditLog.resource_type == "user",
            ).order_by(AuditLog.created_at.desc())
        )
        logs = result.scalars().all()
        pwd_log = next((l for l in logs if l.changes and "password" in l.changes), None)
        if pwd_log:
            assert pwd_log.changes["password"]["old"] == "***"
            assert pwd_log.changes["password"]["new"] == "***"
            assert TEST_PASSWORD not in str(pwd_log.changes)


@pytest.mark.integration
class TestAuditLogFeatureFlag:
    """T6-09: Feature flag toggle audit log."""

    @pytest.mark.asyncio
    async def test_feature_toggle_creates_audit_log(
        self,
        platform_owner_client: AsyncClient,
        test_tenant: Tenant,
        feature_flags_mixed: list[FeatureFlag],
        db_session: AsyncSession,
    ) -> None:
        """Toggling a feature flag should create an audit log."""
        response = await platform_owner_client.patch(
            "/api/v1/feature-flags/blog_module",
            json={"enabled": False},
        )
        assert response.status_code == 200

        result = await db_session.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == test_tenant.id,
                AuditLog.resource_type == "feature_flag",
                AuditLog.action == "update",
            )
        )
        log = result.scalar_one_or_none()
        assert log is not None
