"""Company module database models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import (
    Base,
    PublishableMixin,
    SEOMixin,
    SlugMixin,
    SoftDeleteMixin,
    SortOrderMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


# ============================================================================
# Services
# ============================================================================


class Service(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, PublishableMixin, SortOrderMixin
):
    """Service offered by the company."""

    __tablename__ = "services"

    # Icon or image
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Pricing (optional)
    price_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)

    # Relations
    locales: Mapped[list["ServiceLocale"]] = relationship(
        "ServiceLocale",
        back_populates="service",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    prices: Mapped[list["ServicePrice"]] = relationship(
        "ServicePrice",
        back_populates="service",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    tags: Mapped[list["ServiceTag"]] = relationship(
        "ServiceTag",
        back_populates="service",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_services_tenant", "tenant_id"),
        Index(
            "ix_services_published",
            "tenant_id",
            "is_published",
            postgresql_where="deleted_at IS NULL AND is_published = true",
        ),
        CheckConstraint("price_from IS NULL OR price_from >= 0", name="ck_services_price_positive"),
    )

    def __repr__(self) -> str:
        return f"<Service {self.id}>"


class ServiceLocale(Base, UUIDMixin, TimestampMixin, SlugMixin, SEOMixin):
    """Localized content for services."""

    __tablename__ = "service_locales"

    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relation
    service: Mapped["Service"] = relationship("Service", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("service_id", "locale", name="uq_service_locales"),
        Index("ix_service_locales_slug", "locale", "slug"),
        CheckConstraint("char_length(title) >= 1", name="ck_service_locales_title"),
        CheckConstraint("char_length(slug) >= 2", name="ck_service_locales_slug"),
    )


class ServicePrice(Base, UUIDMixin, TimestampMixin):
    """Price for a service in a specific locale and currency."""

    __tablename__ = "service_prices"

    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)

    # Relation
    service: Mapped["Service"] = relationship("Service", back_populates="prices")

    __table_args__ = (
        UniqueConstraint(
            "service_id", "locale", "currency", name="uq_service_prices_locale_currency"
        ),
        Index("ix_service_prices_service_id", "service_id"),
        Index("ix_service_prices_locale", "service_id", "locale"),
        CheckConstraint("price >= 0", name="ck_service_prices_price_positive"),
        CheckConstraint("currency IN ('RUB', 'USD')", name="ck_service_prices_currency"),
    )


class ServiceTag(Base, UUIDMixin, TimestampMixin):
    """Tag for a service in a specific locale."""

    __tablename__ = "service_tags"

    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)
    tag: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relation
    service: Mapped["Service"] = relationship("Service", back_populates="tags")

    __table_args__ = (
        UniqueConstraint(
            "service_id", "locale", "tag", name="uq_service_tags_locale_tag"
        ),
        Index("ix_service_tags_service_id", "service_id"),
        Index("ix_service_tags_locale", "service_id", "locale"),
        CheckConstraint("char_length(tag) >= 1", name="ck_service_tags_tag_length"),
    )


# ============================================================================
# Practice Areas
# ============================================================================


class PracticeArea(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, PublishableMixin, SortOrderMixin
):
    """Practice area / specialization."""

    __tablename__ = "practice_areas"

    # Icon
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relations
    locales: Mapped[list["PracticeAreaLocale"]] = relationship(
        "PracticeAreaLocale",
        back_populates="practice_area",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    employees: Mapped[list["EmployeePracticeArea"]] = relationship(
        "EmployeePracticeArea",
        back_populates="practice_area",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_practice_areas_tenant", "tenant_id"),
        Index(
            "ix_practice_areas_published",
            "tenant_id",
            "is_published",
            postgresql_where="deleted_at IS NULL AND is_published = true",
        ),
    )


class PracticeAreaLocale(Base, UUIDMixin, TimestampMixin, SlugMixin):
    """Localized content for practice areas."""

    __tablename__ = "practice_area_locales"

    practice_area_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("practice_areas.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relation
    practice_area: Mapped["PracticeArea"] = relationship(
        "PracticeArea", back_populates="locales"
    )

    __table_args__ = (
        UniqueConstraint("practice_area_id", "locale", name="uq_practice_area_locales"),
        Index("ix_practice_area_locales_slug", "locale", "slug"),
    )


# ============================================================================
# Employees / Team
# ============================================================================


class Employee(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, PublishableMixin, SortOrderMixin
):
    """Team member / employee."""

    __tablename__ = "employees"

    # Photo
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Contact info
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Social links (stored as JSON or separate fields)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telegram_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relations
    locales: Mapped[list["EmployeeLocale"]] = relationship(
        "EmployeeLocale",
        back_populates="employee",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    practice_areas: Mapped[list["EmployeePracticeArea"]] = relationship(
        "EmployeePracticeArea",
        back_populates="employee",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_employees_tenant", "tenant_id"),
        Index(
            "ix_employees_published",
            "tenant_id",
            "is_published",
            postgresql_where="deleted_at IS NULL AND is_published = true",
        ),
    )


class EmployeeLocale(Base, UUIDMixin, TimestampMixin, SlugMixin, SEOMixin):
    """Localized content for employees."""

    __tablename__ = "employee_locales"

    employee_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relation
    employee: Mapped["Employee"] = relationship("Employee", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("employee_id", "locale", name="uq_employee_locales"),
        Index("ix_employee_locales_slug", "locale", "slug"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class EmployeePracticeArea(Base, UUIDMixin):
    """Many-to-many between employees and practice areas."""

    __tablename__ = "employee_practice_areas"

    employee_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    practice_area_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("practice_areas.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relations
    employee: Mapped["Employee"] = relationship("Employee", back_populates="practice_areas")
    practice_area: Mapped["PracticeArea"] = relationship(
        "PracticeArea", back_populates="employees"
    )

    __table_args__ = (
        UniqueConstraint("employee_id", "practice_area_id", name="uq_employee_practice_areas"),
    )


# ============================================================================
# Advantages / Benefits
# ============================================================================


class Advantage(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, PublishableMixin, SortOrderMixin
):
    """Company advantage / benefit."""

    __tablename__ = "advantages"

    # Icon
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relations
    locales: Mapped[list["AdvantageLocale"]] = relationship(
        "AdvantageLocale",
        back_populates="advantage",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_advantages_tenant", "tenant_id"),
        Index(
            "ix_advantages_published",
            "tenant_id",
            "is_published",
            postgresql_where="deleted_at IS NULL AND is_published = true",
        ),
    )


class AdvantageLocale(Base, UUIDMixin, TimestampMixin):
    """Localized content for advantages."""

    __tablename__ = "advantage_locales"

    advantage_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("advantages.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relation
    advantage: Mapped["Advantage"] = relationship("Advantage", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("advantage_id", "locale", name="uq_advantage_locales"),
    )


# ============================================================================
# Contacts
# ============================================================================


class Address(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, SortOrderMixin):
    """Company address / office location."""

    __tablename__ = "addresses"

    # Type
    address_type: Mapped[str] = mapped_column(
        String(20), default="office", nullable=False
    )  # office, warehouse, showroom

    # Location
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)

    # Working hours
    working_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Contact for this address
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Is primary address
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relations
    locales: Mapped[list["AddressLocale"]] = relationship(
        "AddressLocale",
        back_populates="address",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_addresses_tenant", "tenant_id"),
        CheckConstraint(
            "address_type IN ('office', 'warehouse', 'showroom', 'other')",
            name="ck_addresses_type",
        ),
    )


class AddressLocale(Base, UUIDMixin, TimestampMixin):
    """Localized content for addresses."""

    __tablename__ = "address_locales"

    address_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("addresses.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # "Main Office"
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    street: Mapped[str] = mapped_column(String(255), nullable=False)
    building: Mapped[str | None] = mapped_column(String(50), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Relation
    address: Mapped["Address"] = relationship("Address", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("address_id", "locale", name="uq_address_locales"),
    )

    @property
    def full_address(self) -> str:
        parts = [self.street]
        if self.building:
            parts.append(self.building)
        if self.city:
            parts.insert(0, self.city)
        if self.postal_code:
            parts.append(self.postal_code)
        return ", ".join(parts)


class Contact(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, SortOrderMixin):
    """General contact information (phone, email, social)."""

    __tablename__ = "contacts"

    # Type: phone, email, whatsapp, telegram, etc.
    contact_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Value
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    # Label (e.g., "Sales", "Support")
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Icon
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Is primary for this type
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_contacts_tenant", "tenant_id"),
        Index("ix_contacts_type", "tenant_id", "contact_type"),
        CheckConstraint(
            "contact_type IN ('phone', 'email', 'whatsapp', 'telegram', 'viber', 'facebook', 'instagram', 'linkedin', 'youtube', 'other')",
            name="ck_contacts_type",
        ),
    )



