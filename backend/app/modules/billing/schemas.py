"""Pydantic schemas for the billing module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Module Schemas
# ============================================================================


class BillingModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    name_ru: str
    description: str | None = None
    description_ru: str | None = None
    category: str
    price_monthly_kopecks: int
    is_base: bool
    sort_order: int


class BillingModuleCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    name_ru: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    description_ru: str | None = None
    category: str = Field(..., min_length=2, max_length=30)
    price_monthly_kopecks: int = Field(default=0, ge=0)
    is_base: bool = False
    sort_order: int = 0


class BillingModuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    name_ru: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    description_ru: str | None = None
    category: str | None = Field(default=None, min_length=2, max_length=30)
    price_monthly_kopecks: int | None = Field(default=None, ge=0)
    is_base: bool | None = None
    sort_order: int | None = None


# ============================================================================
# Plan Schemas
# ============================================================================


class PlanLimits(BaseModel):
    max_users: int | None = None
    max_storage_mb: int | None = None
    max_leads_per_month: int | None = None
    max_products: int | None = None
    max_variants: int | None = None
    max_domains: int | None = None
    max_articles: int | None = None
    max_rbac_roles: int | None = None


class PlanModuleInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    name_ru: str
    category: str
    is_base: bool


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    name_ru: str
    description: str | None = None
    description_ru: str | None = None
    price_monthly_kopecks: int
    price_yearly_kopecks: int
    setup_fee_kopecks: int
    is_default: bool
    is_active: bool
    sort_order: int
    limits: dict
    modules: list[PlanModuleInfo] = []


class PlanCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    name_ru: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    description_ru: str | None = None
    price_monthly_kopecks: int = Field(default=0, ge=0)
    price_yearly_kopecks: int = Field(default=0, ge=0)
    setup_fee_kopecks: int = Field(default=0, ge=0)
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 0
    limits: dict = Field(default_factory=dict)
    module_slugs: list[str] = Field(default_factory=list)


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    name_ru: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    description_ru: str | None = None
    price_monthly_kopecks: int | None = Field(default=None, ge=0)
    price_yearly_kopecks: int | None = Field(default=None, ge=0)
    setup_fee_kopecks: int | None = Field(default=None, ge=0)
    is_default: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    limits: dict | None = None
    module_slugs: list[str] | None = None


# ============================================================================
# Bundle Schemas
# ============================================================================


class BundleModuleInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    name_ru: str


class BundleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    name_ru: str
    description: str | None = None
    description_ru: str | None = None
    price_monthly_kopecks: int
    discount_percent: int
    is_active: bool
    sort_order: int
    modules: list[BundleModuleInfo] = []


class BundleCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    name_ru: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    description_ru: str | None = None
    price_monthly_kopecks: int = Field(default=0, ge=0)
    discount_percent: int = Field(default=0, ge=0, le=100)
    is_active: bool = True
    sort_order: int = 0
    module_slugs: list[str] = Field(default_factory=list)


class BundleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    name_ru: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    description_ru: str | None = None
    price_monthly_kopecks: int | None = Field(default=None, ge=0)
    discount_percent: int | None = Field(default=None, ge=0, le=100)
    is_active: bool | None = None
    sort_order: int | None = None
    module_slugs: list[str] | None = None


# ============================================================================
# TenantModule Schemas
# ============================================================================


class TenantModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    module_id: UUID
    module_slug: str = ""
    module_name: str = ""
    module_name_ru: str = ""
    source: str
    enabled: bool
    activated_at: datetime
    expires_at: datetime | None = None


class TenantModuleCreate(BaseModel):
    """Platform owner manually adding a module to a tenant."""

    module_slug: str = Field(..., min_length=2, max_length=50)
    source: str = Field(default="manual")
    enabled: bool = True


class TenantModuleRemove(BaseModel):
    """Platform owner removing a module from a tenant."""

    module_slug: str = Field(..., min_length=2, max_length=50)


# ============================================================================
# Upgrade Request Schemas
# ============================================================================


class UpgradeRequestCreate(BaseModel):
    request_type: str = Field(..., pattern="^(plan_upgrade|module_addon|bundle_addon)$")
    target_plan_id: UUID | None = None
    target_module_id: UUID | None = None
    target_bundle_id: UUID | None = None
    message: str | None = Field(default=None, max_length=2000)


class UpgradeRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    request_type: str
    target_plan_id: UUID | None = None
    target_module_id: UUID | None = None
    target_bundle_id: UUID | None = None
    status: str
    message: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    target_plan_name: str | None = None
    target_module_name: str | None = None
    target_bundle_name: str | None = None


class UpgradeRequestReview(BaseModel):
    """Platform owner approving or rejecting a request."""

    status: str = Field(..., pattern="^(approved|rejected)$")


# ============================================================================
# MyPlan / MyModules Response Schemas
# ============================================================================


class UsageInfo(BaseModel):
    current: int
    limit: int | None = None
    status: str = "ok"  # ok, warning, exceeded


class MyPlanResponse(BaseModel):
    plan: PlanResponse | None = None
    modules: list[TenantModuleResponse] = []
    usage: dict[str, UsageInfo] = {}


class MyModulesResponse(BaseModel):
    items: list[TenantModuleResponse]
