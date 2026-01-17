"""Tenant-related database models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin, VersionMixin

if TYPE_CHECKING:
    from app.modules.auth.models import AdminUser


class Tenant(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """Tenant (client/organization) model.

    Each tenant represents a separate client with their own data isolation.
    Even in database-per-tenant mode, we keep tenant_id for future SaaS migration.
    """

    __tablename__ = "tenants"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Contact info
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Branding
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # #RRGGBB

    # Custom metadata / extra data
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Relationships
    settings: Mapped["TenantSettings"] = relationship(
        "TenantSettings",
        back_populates="tenant",
        uselist=False,
        lazy="joined",
    )
    feature_flags: Mapped[list["FeatureFlag"]] = relationship(
        "FeatureFlag",
        back_populates="tenant",
        lazy="selectin",
    )
    users: Mapped[list["AdminUser"]] = relationship(
        "AdminUser",
        back_populates="tenant",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_tenants_active", "is_active", postgresql_where="deleted_at IS NULL"),
        CheckConstraint("char_length(slug) >= 2", name="ck_tenants_slug_min_length"),
        CheckConstraint(
            "primary_color IS NULL OR primary_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_tenants_primary_color_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.slug}>"


class TenantSettings(Base, UUIDMixin, TimestampMixin, VersionMixin):
    """Tenant-specific configuration settings."""

    __tablename__ = "tenant_settings"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Default locale
    default_locale: Mapped[str] = mapped_column(String(5), default="ru", nullable=False)

    # Timezone
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow", nullable=False)

    # Date/time formats
    date_format: Mapped[str] = mapped_column(String(20), default="DD.MM.YYYY", nullable=False)
    time_format: Mapped[str] = mapped_column(String(10), default="HH:mm", nullable=False)

    # Notifications
    notify_on_inquiry: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    inquiry_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # SEO defaults
    default_og_image: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Analytics
    ga_tracking_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ym_counter_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relationship
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="settings")

    __table_args__ = (
        CheckConstraint(
            "default_locale ~ '^[a-z]{2}(-[A-Z]{2})?$'",
            name="ck_tenant_settings_locale_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<TenantSettings tenant_id={self.tenant_id}>"


class FeatureFlag(Base, UUIDMixin, TimestampMixin):
    """Feature flags for enabling/disabling functionality per tenant.

    This allows selective enabling of modules like:
    - cases_module: Case studies / portfolio
    - reviews_module: Client testimonials
    - seo_advanced: Advanced SEO features
    - multilang: Multi-language support
    - analytics_advanced: Detailed analytics
    """

    __tablename__ = "feature_flags"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Feature name (e.g., "cases_module", "seo_advanced")
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Is feature enabled
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Optional description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="feature_flags")

    __table_args__ = (
        Index(
            "ix_feature_flags_tenant_feature",
            "tenant_id",
            "feature_name",
            unique=True,
        ),
        Index(
            "ix_feature_flags_enabled",
            "tenant_id",
            "enabled",
            postgresql_where="enabled = true",
        ),
        CheckConstraint(
            "feature_name ~ '^[a-z][a-z0-9_]*$'",
            name="ck_feature_flags_name_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<FeatureFlag {self.feature_name}={self.enabled}>"


# Available feature flags with descriptions
AVAILABLE_FEATURES = {
    "cases_module": "Case studies / portfolio module",
    "reviews_module": "Client testimonials module",
    "seo_advanced": "Advanced SEO features (custom meta per page, redirects)",
    "multilang": "Multi-language content support",
    "analytics_advanced": "Detailed lead analytics (UTM, device, geo)",
    "blog_module": "Blog / articles module",
    "faq_module": "FAQ module",
    "team_module": "Team / employees module",
}

