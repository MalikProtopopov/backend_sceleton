"""Pydantic schemas for the variants module."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Option Group schemas (admin)
# ============================================================================


class OptionValueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    sort_order: int = 0
    color_hex: str | None = Field(default=None, max_length=7)
    image_url: str | None = Field(default=None, max_length=500)


class OptionValueUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    sort_order: int | None = None
    color_hex: str | None = None
    image_url: str | None = None


class OptionValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    sort_order: int
    color_hex: str | None = None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime


class OptionGroupCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    display_type: str = Field(
        default="dropdown",
        pattern="^(dropdown|buttons|color_swatch|cards)$",
    )
    sort_order: int = 0
    is_required: bool = True
    parameter_id: UUID | None = None
    values: list[OptionValueCreate] = Field(default_factory=list)


class OptionGroupUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    display_type: str | None = Field(
        default=None,
        pattern="^(dropdown|buttons|color_swatch|cards)$",
    )
    sort_order: int | None = None
    is_required: bool | None = None
    parameter_id: UUID | None = None


class OptionGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    title: str
    slug: str
    display_type: str
    sort_order: int
    is_required: bool
    parameter_id: UUID | None = None
    values: list[OptionValueResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Variant Price schemas (admin)
# ============================================================================


class VariantPriceCreate(BaseModel):
    price_type: str = Field(default="regular", pattern="^(regular|sale|wholesale|cost)$")
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="RUB", max_length=3)
    valid_from: date | None = None
    valid_to: date | None = None


class VariantPriceUpdate(BaseModel):
    price_type: str | None = Field(default=None, pattern="^(regular|sale|wholesale|cost)$")
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    valid_from: date | None = None
    valid_to: date | None = None


class VariantPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    price_type: str
    amount: Decimal
    currency: str
    valid_from: date | None = None
    valid_to: date | None = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Variant Inclusion schemas (admin)
# ============================================================================


class VariantInclusionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    is_included: bool = True
    sort_order: int = 0
    icon: str | None = Field(default=None, max_length=100)
    group: str | None = Field(default=None, max_length=100)


class VariantInclusionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    is_included: bool | None = None
    sort_order: int | None = None
    icon: str | None = None
    group: str | None = None


class VariantInclusionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None = None
    is_included: bool
    sort_order: int
    icon: str | None = None
    group: str | None = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Variant Image schemas (admin)
# ============================================================================


class VariantImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    alt: str | None = None
    width: int | None = None
    height: int | None = None
    size_bytes: int | None = None
    mime_type: str | None = None
    sort_order: int
    is_cover: bool
    created_at: datetime


# ============================================================================
# Variant schemas (admin)
# ============================================================================


class VariantCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 0
    stock_quantity: int | None = None
    weight: Decimal | None = None
    option_value_ids: list[UUID] = Field(default_factory=list)


class VariantUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    is_default: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    stock_quantity: int | None = None
    weight: Decimal | None = None
    option_value_ids: list[UUID] | None = None


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    tenant_id: UUID
    sku: str
    slug: str
    title: str
    description: str | None = None
    is_default: bool
    is_active: bool
    sort_order: int
    stock_quantity: int | None = None
    weight: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class VariantDetailResponse(VariantResponse):
    """Enriched variant response with nested prices, options, inclusions, images."""

    prices: list[VariantPriceResponse] = Field(default_factory=list)
    option_values: list[OptionValueResponse] = Field(default_factory=list)
    inclusions: list[VariantInclusionResponse] = Field(default_factory=list)
    images: list[VariantImageResponse] = Field(default_factory=list)


# ============================================================================
# Matrix generation
# ============================================================================


class VariantGenerateRequest(BaseModel):
    option_group_ids: list[UUID] = Field(..., min_length=1)
    base_price: Decimal | None = Field(default=None, ge=0)


class VariantGenerateResponse(BaseModel):
    created_count: int
    variants: list[VariantResponse]


# ============================================================================
# Public schemas
# ============================================================================


class OptionValuePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    slug: str
    color_hex: str | None = None
    image_url: str | None = None


class OptionGroupPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    slug: str
    display_type: str
    values: list[OptionValuePublic] = Field(default_factory=list)


class VariantPricePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price_type: str
    amount: Decimal
    currency: str


class VariantInclusionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str | None = None
    is_included: bool
    icon: str | None = None
    group: str | None = None


class VariantImagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    alt: str | None = None
    sort_order: int
    is_cover: bool


class VariantPublic(BaseModel):
    id: UUID
    slug: str
    title: str
    sku: str
    description: str | None = None
    is_default: bool
    in_stock: bool
    sort_order: int
    prices: list[VariantPricePublic] = Field(default_factory=list)
    options: dict[str, str] = Field(default_factory=dict)
    images: list[VariantImagePublic] = Field(default_factory=list)
    inclusions: list[VariantInclusionPublic] = Field(default_factory=list)
