"""Localization database models."""

from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import Base, SortOrderMixin, TimestampMixin, UUIDMixin


class LocaleConfig(Base, UUIDMixin, TimestampMixin, SortOrderMixin):
    """Locale configuration per tenant.

    Defines which languages are available for a tenant and their settings.
    """

    __tablename__ = "locale_configs"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Locale code (e.g., 'ru', 'en', 'de')
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Display name (e.g., 'Русский', 'English')
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Native name for display
    native_name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Is this locale enabled
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Is this the default locale for the tenant
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # RTL support
    is_rtl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index(
            "ix_locale_configs_tenant_locale",
            "tenant_id",
            "locale",
            unique=True,
        ),
        Index(
            "ix_locale_configs_tenant_default",
            "tenant_id",
            postgresql_where="is_default = true",
        ),
        Index(
            "ix_locale_configs_tenant_enabled",
            "tenant_id",
            "is_enabled",
            postgresql_where="is_enabled = true",
        ),
        CheckConstraint(
            "locale ~ '^[a-z]{2}(-[A-Z]{2})?$'",
            name="ck_locale_configs_locale_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<LocaleConfig {self.locale} (default={self.is_default})>"


# Default locales with their configuration
DEFAULT_LOCALES = [
    {
        "locale": "ru",
        "name": "Russian",
        "native_name": "Русский",
        "is_default": True,
        "is_rtl": False,
    },
    {
        "locale": "en",
        "name": "English",
        "native_name": "English",
        "is_default": False,
        "is_rtl": False,
    },
]

