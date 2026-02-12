"""Notification models - Email log for tracking all send attempts."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import Base, TimestampMixin, UUIDMixin


class EmailLog(Base, UUIDMixin, TimestampMixin):
    """Log of all sent emails for debugging and auditing.

    Every email send attempt (success or failure) is recorded here,
    enabling admins to verify invitation delivery and diagnose issues.
    """

    __tablename__ = "email_logs"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    email_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="welcome, password_reset, inquiry, test",
    )
    provider: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="smtp, sendgrid, mailgun, console",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="sent, failed, console",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_email_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_email_logs_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<EmailLog {self.email_type} to={self.to_email} status={self.status}>"
