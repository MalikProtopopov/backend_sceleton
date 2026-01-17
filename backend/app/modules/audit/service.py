"""Audit module service layer."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import AdminUser, AuditLog
from app.modules.audit.schemas import (
    AuditLogCreate,
    AuditLogResponse,
    AuditUserResponse,
)


class AuditLogService:
    """Service for managing audit logs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_logs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 25,
        user_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: UUID | None = None,
        action: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[AuditLog], int]:
        """List audit logs with pagination and filters."""
        base_query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if user_id:
            base_query = base_query.where(AuditLog.user_id == user_id)

        if resource_type:
            base_query = base_query.where(AuditLog.resource_type == resource_type)

        if resource_id:
            base_query = base_query.where(AuditLog.resource_id == resource_id)

        if action:
            base_query = base_query.where(AuditLog.action == action)

        if date_from:
            base_query = base_query.where(
                AuditLog.created_at >= datetime.combine(date_from, datetime.min.time())
            )

        if date_to:
            base_query = base_query.where(
                AuditLog.created_at <= datetime.combine(date_to, datetime.max.time())
            )

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results with user relationship
        stmt = (
            base_query
            .options(selectinload(AuditLog.user))
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        logs = list(result.scalars().all())

        return logs, total

    def to_response(self, log: AuditLog) -> AuditLogResponse:
        """Convert audit log to response schema."""
        user = None
        if log.user_id and hasattr(log, 'user') and log.user:
            user = AuditUserResponse(
                id=log.user_id,
                email=log.user.email,
                name=log.user.full_name,
            )
        elif log.user_id:
            user = AuditUserResponse(
                id=log.user_id,
                email=None,
                name=None,
            )

        return AuditLogResponse(
            id=log.id,
            timestamp=log.created_at,  # Use created_at instead of timestamp
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            resource_name=None,  # Not in auth model
            user=user,
            changes=log.changes,
            ip_address=log.ip_address,
            status="success",  # Not in auth model, default to success
        )

