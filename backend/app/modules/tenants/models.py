"""Tenant-related database models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
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

    # Email / SMTP configuration (per-tenant)
    email_provider: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Email provider: smtp, sendgrid, mailgun, console. NULL = use global default",
    )
    email_from_address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Sender email address for this tenant",
    )
    email_from_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Sender display name for this tenant",
    )
    smtp_host: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="SMTP server host (e.g. smtp.gmail.com)",
    )
    smtp_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=587,
        comment="SMTP server port (587=STARTTLS, 465=SSL)",
    )
    smtp_user: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="SMTP authentication username",
    )
    smtp_password_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="SMTP password (encrypted with Fernet)",
    )
    smtp_use_tls: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Use STARTTLS for SMTP connection",
    )
    email_api_key_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="SendGrid/Mailgun API key (encrypted with Fernet)",
    )

    # SEO defaults
    default_og_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # SEO domain validation
    allowed_domains: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="List of allowed domains for sitemap/robots base_url validation (e.g., ['mediann.dev', '*.mediann.dev'])",
    )
    # SEO frontend base URL (used in sitemap <loc> and robots.txt Sitemap:)
    site_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Frontend base URL for sitemap/robots (e.g. https://mediann.dev). Used in <loc> and Sitemap: directive.",
    )
    
    # SEO sitemap configuration
    sitemap_static_pages: Mapped[list[dict] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Static pages for sitemap [{path, priority, changefreq}]",
    )
    
    # SEO robots.txt customization
    robots_txt_custom_rules: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Custom rules to append to robots.txt",
    )
    
    # IndexNow integration
    indexnow_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="IndexNow API key for search engine notification",
    )
    indexnow_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Enable IndexNow URL submission",
    )
    
    # AI discovery (llms.txt)
    llms_txt_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Enable llms.txt generation for AI discovery",
    )
    llms_txt_custom_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Custom content to include in llms.txt",
    )

    # Analytics
    ga_tracking_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ym_counter_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Yandex.Metrika counter ID or embed code",
    )

    # Relationship
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="settings")

    __table_args__ = (
        CheckConstraint(
            "default_locale ~ '^[a-z]{2}(-[A-Z]{2})?$'",
            name="ck_tenant_settings_locale_format",
        ),
        CheckConstraint(
            "email_provider IS NULL OR email_provider IN ('smtp', 'sendgrid', 'mailgun', 'console')",
            name="ck_tenant_settings_email_provider",
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
AVAILABLE_FEATURES: dict[str, dict[str, str]] = {
    "blog_module": {
        "title": "Blog / Articles",
        "title_ru": "Блог / Статьи",
        "description": "Create and manage articles and blog posts",
        "description_ru": "Создание и управление статьями и блогом",
        "category": "content",
    },
    "cases_module": {
        "title": "Case Studies",
        "title_ru": "Кейсы / Портфолио",
        "description": "Publish case studies and portfolio items",
        "description_ru": "Публикация кейсов и портфолио работ",
        "category": "content",
    },
    "reviews_module": {
        "title": "Reviews / Testimonials",
        "title_ru": "Отзывы",
        "description": "Manage client testimonials and reviews",
        "description_ru": "Управление отзывами клиентов",
        "category": "content",
    },
    "faq_module": {
        "title": "FAQ",
        "title_ru": "Вопросы и ответы",
        "description": "Manage frequently asked questions",
        "description_ru": "Управление часто задаваемыми вопросами",
        "category": "content",
    },
    "team_module": {
        "title": "Team / Employees",
        "title_ru": "Команда / Сотрудники",
        "description": "Manage team members and employee profiles",
        "description_ru": "Управление профилями сотрудников",
        "category": "company",
    },
    "services_module": {
        "title": "Services",
        "title_ru": "Услуги",
        "description": "Manage company services and practice areas",
        "description_ru": "Управление услугами и направлениями деятельности",
        "category": "company",
    },
    "seo_advanced": {
        "title": "Advanced SEO",
        "title_ru": "Расширенное SEO",
        "description": "Advanced SEO features (custom meta per page, redirects)",
        "description_ru": "Расширенные SEO-функции (мета-теги, редиректы)",
        "category": "platform",
    },
    "multilang": {
        "title": "Multi-language",
        "title_ru": "Мультиязычность",
        "description": "Multi-language content support",
        "description_ru": "Поддержка мультиязычного контента",
        "category": "platform",
    },
    "analytics_advanced": {
        "title": "Advanced Analytics",
        "title_ru": "Расширенная аналитика",
        "description": "Detailed lead analytics (UTM, device, geo)",
        "description_ru": "Детальная аналитика лидов (UTM, устройства, гео)",
        "category": "platform",
    },
}


def get_feature_description(feature_name: str) -> str:
    """Get simple description for backward compatibility."""
    feature = AVAILABLE_FEATURES.get(feature_name, {})
    return feature.get("description", feature_name)

