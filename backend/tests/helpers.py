"""Shared test helpers for assertion, login, and data manipulation."""

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AuditLog
from app.modules.tenants.models import FeatureFlag, Tenant


def assert_error_response(
    response: httpx.Response,
    status_code: int,
    error_code: str,
    detail_subset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assert response matches RFC 7807 error shape and return parsed body.

    Args:
        response: httpx response object.
        status_code: Expected HTTP status code.
        error_code: Expected error_code (last segment of ``type`` URL).
        detail_subset: Optional dict of extra fields that must be present in body.

    Returns:
        Parsed JSON body dict.
    """
    assert response.status_code == status_code, (
        f"Expected {status_code}, got {response.status_code}: {response.text}"
    )
    body = response.json()
    # RFC 7807 shape
    assert "detail" in body or "type" in body, f"Missing RFC 7807 fields: {body}"
    # Unwrap: FastAPI puts our dict under 'detail' key at the top level
    detail = body if "type" in body else body.get("detail", body)
    # Handle case where detail is a string (plain FastAPI error)
    if isinstance(detail, str):
        pytest.fail(
            f"Expected RFC 7807 error with code '{error_code}', "
            f"got plain string detail: {detail!r}"
        )
    assert detail.get("type", "").endswith(f"/{error_code}"), (
        f"Expected error_code '{error_code}', got type='{detail.get('type')}'"
    )
    if detail_subset:
        for key, value in detail_subset.items():
            assert key in detail, f"Missing key '{key}' in response detail: {detail}"
            assert detail[key] == value, (
                f"Expected detail['{key}']={value!r}, got {detail[key]!r}"
            )
    return detail


async def assert_audit_entry(
    db_session: AsyncSession,
    tenant_id: UUID,
    resource_type: str,
    action: str,
    resource_id: UUID | None = None,
    changes_subset: dict[str, Any] | None = None,
) -> AuditLog:
    """Query the most recent audit entry matching criteria and assert fields.

    Returns:
        The matched AuditLog row.
    """
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .where(AuditLog.resource_type == resource_type)
        .where(AuditLog.action == action)
    )
    if resource_id is not None:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(1)

    result = await db_session.execute(stmt)
    entry = result.scalar_one_or_none()
    assert entry is not None, (
        f"No audit entry found for {resource_type}/{action} in tenant {tenant_id}"
    )
    if changes_subset and entry.changes:
        for key, value in changes_subset.items():
            assert key in entry.changes, (
                f"Missing key '{key}' in audit changes: {entry.changes}"
            )
            assert entry.changes[key] == value, (
                f"Expected changes['{key}']={value!r}, got {entry.changes[key]!r}"
            )
    return entry


async def login_as(
    client: httpx.AsyncClient,
    email: str,
    password: str,
    tenant_id: UUID,
) -> dict[str, Any]:
    """Login via API and return response JSON (tokens + user)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers={"X-Tenant-ID": str(tenant_id)},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()


async def set_feature_flag(
    db_session: AsyncSession,
    tenant_id: UUID,
    feature_name: str,
    enabled: bool,
) -> None:
    """Set a feature flag value directly in the DB."""
    stmt = (
        select(FeatureFlag)
        .where(FeatureFlag.tenant_id == tenant_id)
        .where(FeatureFlag.feature_name == feature_name)
    )
    result = await db_session.execute(stmt)
    flag = result.scalar_one_or_none()
    if flag:
        flag.enabled = enabled
    else:
        flag = FeatureFlag(
            tenant_id=tenant_id,
            feature_name=feature_name,
            enabled=enabled,
            description=f"Test flag: {feature_name}",
        )
        db_session.add(flag)
    await db_session.flush()


async def deactivate_tenant(
    db_session: AsyncSession,
    tenant_id: UUID,
) -> None:
    """Set tenant is_active=False directly in the DB."""
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    result = await db_session.execute(stmt)
    tenant = result.scalar_one()
    tenant.is_active = False
    await db_session.flush()
