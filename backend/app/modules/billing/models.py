"""Billing database models: modules, plans, bundles, tenant access, upgrade requests."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.modules.auth.models import AdminUser
    from app.modules.tenants.models import Tenant


class ModuleCategory(str, Enum):
    CONTENT = "content"
    COMPANY = "company"
    CRM = "crm"
    PLATFORM = "platform"
    COMMERCE = "commerce"


class TenantModuleSource(str, Enum):
    PLAN = "plan"
    ADDON = "addon"
    BUNDLE = "bundle"
    MANUAL = "manual"


class UpgradeRequestType(str, Enum):
    PLAN_UPGRADE = "plan_upgrade"
    MODULE_ADDON = "module_addon"
    BUNDLE_ADDON = "bundle_addon"


class UpgradeRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BillingModule(Base, UUIDMixin, TimestampMixin):
    """Catalog of available billing modules (features that can be sold)."""

    __tablename__ = "billing_modules"

    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    price_monthly_kopecks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_base: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    plan_links: Mapped[list["PlanModule"]] = relationship("PlanModule", back_populates="module", lazy="selectin")
    bundle_links: Mapped[list["BundleModule"]] = relationship("BundleModule", back_populates="module", lazy="selectin")

    __table_args__ = (
        CheckConstraint("price_monthly_kopecks >= 0", name="ck_billing_modules_price_positive"),
    )

    def __repr__(self) -> str:
        return f"<BillingModule {self.slug}>"


class Plan(Base, UUIDMixin, TimestampMixin):
    """Tariff plan with included modules and resource limits."""

    __tablename__ = "billing_plans"

    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly_kopecks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price_yearly_kopecks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    setup_fee_kopecks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    limits: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    module_links: Mapped[list["PlanModule"]] = relationship("PlanModule", back_populates="plan", lazy="selectin")

    __table_args__ = (
        CheckConstraint("price_monthly_kopecks >= 0", name="ck_billing_plans_price_positive"),
        CheckConstraint("setup_fee_kopecks >= 0", name="ck_billing_plans_setup_fee_positive"),
    )

    @property
    def modules(self) -> list["BillingModule"]:
        return [link.module for link in self.module_links]

    def get_limit(self, resource: str) -> int | None:
        """Get a specific limit value. Returns None if limit is not set (unlimited)."""
        val = self.limits.get(resource)
        if val is None or val == -1:
            return None
        return val

    def __repr__(self) -> str:
        return f"<Plan {self.slug}>"


class PlanModule(Base, UUIDMixin):
    """Many-to-many: which modules are included in which plans."""

    __tablename__ = "billing_plan_modules"

    plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_plans.id", ondelete="CASCADE"), nullable=False
    )
    module_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_modules.id", ondelete="CASCADE"), nullable=False
    )

    plan: Mapped["Plan"] = relationship("Plan", back_populates="module_links")
    module: Mapped["BillingModule"] = relationship("BillingModule", back_populates="plan_links")

    __table_args__ = (
        UniqueConstraint("plan_id", "module_id", name="uq_plan_module"),
    )


class Bundle(Base, UUIDMixin, TimestampMixin):
    """Thematic bundle of modules sold at a discount."""

    __tablename__ = "billing_bundles"

    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_monthly_kopecks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    module_links: Mapped[list["BundleModule"]] = relationship("BundleModule", back_populates="bundle", lazy="selectin")

    __table_args__ = (
        CheckConstraint("price_monthly_kopecks >= 0", name="ck_billing_bundles_price_positive"),
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="ck_billing_bundles_discount_range"),
    )

    @property
    def modules(self) -> list["BillingModule"]:
        return [link.module for link in self.module_links]

    def __repr__(self) -> str:
        return f"<Bundle {self.slug}>"


class BundleModule(Base, UUIDMixin):
    """Many-to-many: which modules are included in which bundles."""

    __tablename__ = "billing_bundle_modules"

    bundle_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_bundles.id", ondelete="CASCADE"), nullable=False
    )
    module_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_modules.id", ondelete="CASCADE"), nullable=False
    )

    bundle: Mapped["Bundle"] = relationship("Bundle", back_populates="module_links")
    module: Mapped["BillingModule"] = relationship("BillingModule", back_populates="bundle_links")

    __table_args__ = (
        UniqueConstraint("bundle_id", "module_id", name="uq_bundle_module"),
    )


class TenantModule(Base, UUIDMixin, TimestampMixin):
    """Which billing modules are active for a tenant and how they were acquired."""

    __tablename__ = "tenant_modules"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_modules.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False, default=TenantModuleSource.PLAN.value)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    module: Mapped["BillingModule"] = relationship("BillingModule", lazy="joined")

    __table_args__ = (
        UniqueConstraint("tenant_id", "module_id", "source", name="uq_tenant_module_source"),
        Index("ix_tenant_modules_lookup", "tenant_id", "enabled"),
        CheckConstraint(
            "source IN ('plan', 'addon', 'bundle', 'manual')",
            name="ck_tenant_modules_source",
        ),
    )

    def __repr__(self) -> str:
        return f"<TenantModule tenant={self.tenant_id} module={self.module_id} source={self.source}>"


class UpgradeRequest(Base, UUIDMixin, TimestampMixin):
    """Tenant owner request to upgrade plan or purchase addon modules/bundles."""

    __tablename__ = "upgrade_requests"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_plan_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_plans.id", ondelete="SET NULL"), nullable=True
    )
    target_module_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_modules.id", ondelete="SET NULL"), nullable=True
    )
    target_bundle_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("billing_bundles.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UpgradeRequestStatus.PENDING.value
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    target_plan: Mapped["Plan | None"] = relationship("Plan", foreign_keys=[target_plan_id], lazy="joined")
    target_module: Mapped["BillingModule | None"] = relationship("BillingModule", foreign_keys=[target_module_id], lazy="joined")
    target_bundle: Mapped["Bundle | None"] = relationship("Bundle", foreign_keys=[target_bundle_id], lazy="joined")
    reviewer: Mapped["AdminUser | None"] = relationship("AdminUser", foreign_keys=[reviewed_by], lazy="selectin")

    __table_args__ = (
        Index("ix_upgrade_requests_status", "tenant_id", "status"),
        CheckConstraint(
            "request_type IN ('plan_upgrade', 'module_addon', 'bundle_addon')",
            name="ck_upgrade_requests_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_upgrade_requests_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<UpgradeRequest {self.id} {self.request_type} status={self.status}>"
