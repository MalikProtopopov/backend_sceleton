"""Audit log database models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, UUIDMixin

if TYPE_CHECKING:
    from app.modules.auth.models import AdminUser


class AuditLog(Base, UUIDMixin):
    """Audit log for tracking all changes.

    Records who did what, when, and what changed.
    Note: Audit logs are immutable, so no updated_at field.
    """

    __tablename__ = "audit_logs"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    user: Mapped["AdminUser | None"] = relationship("AdminUser", lazy="selectin")

    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

    action: Mapped[str] = mapped_column(String(20), nullable=False)

    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_logs_tenant_resource", "tenant_id", "resource_type", "resource_id"),
        Index("ix_audit_logs_resource_id", "resource_id"),
        Index("ix_audit_logs_user", "user_id"),
        Index("ix_audit_logs_created", "tenant_id", "created_at"),
        CheckConstraint(
            "action IN ('create', 'update', 'delete', 'login', 'logout')",
            name="ck_audit_logs_action",
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type}/{self.resource_id}>"
