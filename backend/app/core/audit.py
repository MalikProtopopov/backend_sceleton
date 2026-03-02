"""Shared audit logging service.

Provides a centralized service for creating audit log entries across
all modules (users, tenants, feature flags, roles, auth).
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.audit.models import AuditLog

logger = get_logger(__name__)


class AuditService:
    """Service for creating audit log entries.

    Usage:
        audit = AuditService(db)
        await audit.log(
            tenant_id=tenant_id,
            user_id=current_user.id,
            resource_type="user",
            resource_id=new_user.id,
            action="create",
        )
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        tenant_id: UUID,
        user_id: UUID | None,
        resource_type: str,
        resource_id: UUID,
        action: str,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            tenant_id: Tenant context
            user_id: User who performed the action (None for system actions)
            resource_type: Type of resource (e.g., 'user', 'tenant', 'feature_flag', 'role', 'auth')
            resource_id: ID of the affected resource
            action: Action performed ('create', 'update', 'delete', 'login', 'logout')
            changes: Dict of changes for updates, format: {"field": {"old": ..., "new": ...}}
            ip_address: Client IP address
            user_agent: Client user agent string

        Returns:
            Created AuditLog entry
        """
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)

        logger.debug(
            "audit_log_created",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id),
            user_id=str(user_id) if user_id else None,
        )

        return entry
