"""API routes for audit module."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.audit.schemas import AuditLogListResponse
from app.modules.audit.service import AuditLogService

router = APIRouter(tags=["Admin - Audit"])


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    summary="List audit logs",
    dependencies=[Depends(PermissionChecker("audit:read"))],
)
async def list_audit_logs(
    pagination: Pagination,
    user_id: UUID | None = Query(default=None, alias="userId"),
    resource_type: str | None = Query(default=None, alias="resourceType"),
    resource_id: UUID | None = Query(default=None, alias="resourceId"),
    action: str | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """List audit logs with filters.

    Filters:
    - userId: Filter by user who performed the action
    - resourceType: Filter by resource type (article, case, employee, etc.)
    - resourceId: Filter by specific resource ID
    - action: Filter by action type (create, update, delete, publish, etc.)
    - dateFrom: Filter by start date (inclusive)
    - dateTo: Filter by end date (inclusive)
    """
    service = AuditLogService(db)
    logs, total = await service.list_logs(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
    )

    return AuditLogListResponse(
        items=[service.to_response(log) for log in logs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )

