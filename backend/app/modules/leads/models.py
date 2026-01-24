"""Leads module database models."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import (
    Base,
    SoftDeleteMixin,
    SortOrderMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


class InquiryStatus(str, Enum):
    """Inquiry processing status."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    CONTACTED = "contacted"
    COMPLETED = "completed"
    SPAM = "spam"
    CANCELLED = "cancelled"


# ============================================================================
# Inquiry Forms
# ============================================================================


class InquiryForm(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Inquiry form configuration.

    Different forms for different purposes:
    - Contact form
    - Service request
    - Consultation booking
    - Quote request
    """

    __tablename__ = "inquiry_forms"

    # Form identifier (used in frontend)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)

    # Form name for admin
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Is form active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Email to send notifications
    notification_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Success message (can be localized via JSON)
    success_message: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Required fields configuration
    fields_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relations
    inquiries: Mapped[list["Inquiry"]] = relationship(
        "Inquiry",
        back_populates="form",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_inquiry_forms_tenant", "tenant_id"),
        Index("ix_inquiry_forms_slug", "tenant_id", "slug", unique=True),
        CheckConstraint("char_length(slug) >= 2", name="ck_inquiry_forms_slug_min"),
    )

    def __repr__(self) -> str:
        return f"<InquiryForm {self.slug}>"


# ============================================================================
# Inquiries (Leads)
# ============================================================================


class Inquiry(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """Customer inquiry / lead with full analytics tracking.

    Captures all important data for lead analytics:
    - Contact info
    - Source tracking (UTM, referrer)
    - Device/browser info
    - Page context
    """

    __tablename__ = "inquiries"

    # Form reference
    form_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("inquiry_forms.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=InquiryStatus.NEW.value,
        nullable=False,
        index=True,
    )

    # ========== Contact Info ==========
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Message/comment
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ========== Service Context ==========
    # Which service/page the inquiry is about
    service_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ========== Source Tracking (UTM) ==========
    # UTM parameters for campaign tracking
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Referrer
    referrer_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # ========== Page Context ==========
    # URL where form was submitted
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # Page path (for analytics grouping)
    page_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Page title at submission time
    page_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ========== Device & Browser ==========
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # desktop, mobile, tablet
    browser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    os: Mapped[str | None] = mapped_column(String(100), nullable=True)
    screen_resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ========== Location ==========
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ========== Session Info ==========
    # Client-side session ID for tracking user journey
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Number of page views in this session before submission
    session_page_views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Time spent on page before submission (seconds)
    time_on_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ========== Custom Data ==========
    # Any additional form fields as JSON
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ========== Processing Info ==========
    # Assigned manager
    assigned_to: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Internal notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # When was this inquiry contacted
    contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Notification sent
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relations
    form: Mapped["InquiryForm | None"] = relationship(
        "InquiryForm", back_populates="inquiries"
    )

    __table_args__ = (
        Index("ix_inquiries_tenant", "tenant_id"),
        Index("ix_inquiries_status", "tenant_id", "status"),
        Index("ix_inquiries_created", "tenant_id", "created_at"),
        Index("ix_inquiries_form", "form_id"),
        Index("ix_inquiries_service", "service_id"),
        Index("ix_inquiries_assigned", "assigned_to"),
        # Analytics indexes
        Index("ix_inquiries_utm_source", "tenant_id", "utm_source"),
        Index("ix_inquiries_utm_campaign", "tenant_id", "utm_campaign"),
        Index("ix_inquiries_device", "tenant_id", "device_type"),
        CheckConstraint(
            "status IN ('new', 'in_progress', 'contacted', 'completed', 'spam', 'cancelled')",
            name="ck_inquiries_status",
        ),
        CheckConstraint(
            "device_type IS NULL OR device_type IN ('desktop', 'mobile', 'tablet', 'other')",
            name="ck_inquiries_device_type",
        ),
    )

    @property
    def has_utm(self) -> bool:
        """Check if inquiry has any UTM parameters."""
        return any([
            self.utm_source,
            self.utm_medium,
            self.utm_campaign,
        ])

    def mark_contacted(self) -> None:
        """Mark inquiry as contacted."""
        self.status = InquiryStatus.CONTACTED.value
        self.contacted_at = datetime.utcnow()

    def mark_completed(self) -> None:
        """Mark inquiry as completed."""
        self.status = InquiryStatus.COMPLETED.value

    def mark_spam(self) -> None:
        """Mark inquiry as spam."""
        self.status = InquiryStatus.SPAM.value

    def __repr__(self) -> str:
        return f"<Inquiry {self.id} status={self.status}>"

