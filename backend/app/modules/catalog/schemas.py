"""Pydantic schemas for catalog module."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.content_blocks.schemas import ContentBlockResponse


# ============================================================================
# UOM Schemas
# ============================================================================


class UOMCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    symbol: str | None = Field(default=None, max_length=20)


class UOMUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    code: str | None = Field(default=None, max_length=20)
    symbol: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


class UOMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    symbol: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Category Schemas
# ============================================================================


class CategoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255)
    parent_id: UUID | None = None
    description: str | None = Field(default=None, max_length=10000)
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    parent_id: UUID | None = None
    description: str | None = Field(default=None, max_length=10000)
    image_url: str | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    title: str
    slug: str
    parent_id: UUID | None = None
    description: str | None = None
    image_url: str | None = None
    is_active: bool
    sort_order: int
    version: int
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int


class CategoryTreeResponse(BaseModel):
    items: list[CategoryResponse]
    total: int


# ============================================================================
# Product Schemas
# ============================================================================


class ProductCreate(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=255)
    title: str = Field(..., min_length=1, max_length=500)
    brand: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    uom_id: UUID | None = None
    is_active: bool = True
    product_type: str = Field(
        default="physical",
        pattern="^(physical|digital|service|course|subscription)$",
    )
    category_ids: list[UUID] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    brand: str | None = None
    model: str | None = None
    description: str | None = Field(default=None, max_length=10000)
    uom_id: UUID | None = None
    is_active: bool | None = None
    product_type: str | None = Field(
        default=None,
        pattern="^(physical|digital|service|course|subscription)$",
    )
    has_variants: bool | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class ProductImageResponse(BaseModel):
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


class ProductAliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    alias: str


class ProductCategoryLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    is_primary: bool


class ProductPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    price_type: str
    amount: Decimal
    currency: str
    valid_from: date | None = None
    valid_to: date | None = None
    created_at: datetime
    updated_at: datetime


class ProductAnalogResponse(BaseModel):
    analog_product_id: UUID
    sku: str
    title: str
    relation: str
    notes: str | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    sku: str
    slug: str
    title: str
    brand: str | None = None
    model: str | None = None
    description: str | None = None
    uom_id: UUID | None = None
    is_active: bool
    product_type: str = "physical"
    has_variants: bool = False
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageResponse] = Field(default_factory=list)


class ProductDetailResponse(ProductResponse):
    """Extended response with optionally loaded relations."""

    aliases: list[ProductAliasResponse] = Field(default_factory=list)
    categories: list[ProductCategoryLinkResponse] = Field(default_factory=list)
    prices: list[ProductPriceResponse] = Field(default_factory=list)


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Alias schemas
# ============================================================================


class ProductAliasCreate(BaseModel):
    aliases: list[str] = Field(..., min_length=1)


class ProductAliasBulkResponse(BaseModel):
    created: int
    skipped: int


# ============================================================================
# Analog schemas
# ============================================================================


class ProductAnalogCreate(BaseModel):
    analog_product_id: UUID
    relation: str = Field(default="equivalent", pattern="^(equivalent|better|worse)$")
    notes: str | None = None


# ============================================================================
# Price schemas
# ============================================================================


class ProductPriceCreate(BaseModel):
    price_type: str = Field(default="regular", pattern="^(regular|sale|wholesale|cost)$")
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="RUB", max_length=3)
    valid_from: date | None = None
    valid_to: date | None = None


class ProductPriceUpdate(BaseModel):
    price_type: str | None = Field(default=None, pattern="^(regular|sale|wholesale|cost)$")
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)
    valid_from: date | None = None
    valid_to: date | None = None


# ============================================================================
# Image schemas
# ============================================================================


class ProductImageUpdateRequest(BaseModel):
    alt: str | None = None
    sort_order: int | None = None


class ProductImageReorderRequest(BaseModel):
    ordered_ids: list[UUID]


# ============================================================================
# Public (client-facing) schemas
# ============================================================================


class CategoryPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    parent_id: UUID | None = None
    description: str | None = None
    image_url: str | None = None


class CategoryPublicTreeResponse(BaseModel):
    items: list[CategoryPublicResponse]
    total: int


class ProductImagePublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    alt: str | None = None
    width: int | None = None
    height: int | None = None
    sort_order: int
    is_cover: bool


class ProductPricePublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price_type: str
    amount: Decimal
    currency: str


class UOMPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    symbol: str | None = None


class CharacteristicValuePublic(BaseModel):
    slug: str
    label: str


class ProductCharacteristicPublicResponse(BaseModel):
    parameter_slug: str
    parameter_name: str
    type: str
    values: list[CharacteristicValuePublic] = Field(default_factory=list)
    value_text: str | None = None
    value_number: Decimal | None = None
    value_bool: bool | None = None
    uom: UOMPublicResponse | None = None


class ProductCharPublicResponse(BaseModel):
    """Backward-compatible flat characteristic for product card."""
    name: str
    value_text: str


class ProductPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    sku: str
    title: str
    brand: str | None = None
    model: str | None = None
    description: str | None = None
    product_type: str = "physical"
    has_variants: bool = False
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    cover_url: str | None = None


class ProductPublicDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    sku: str
    title: str
    brand: str | None = None
    model: str | None = None
    description: str | None = None
    product_type: str = "physical"
    has_variants: bool = False
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    images: list[ProductImagePublicResponse] = Field(default_factory=list)
    characteristics: list[ProductCharacteristicPublicResponse] = Field(default_factory=list)
    chars: list[ProductCharPublicResponse] = Field(default_factory=list)
    categories: list[CategoryPublicResponse] = Field(default_factory=list)
    prices: list[ProductPricePublicResponse] = Field(default_factory=list)
    content_blocks: list[ContentBlockResponse] = Field(default_factory=list)
    # Variant data (populated when has_variants=true and variants_module enabled)
    option_groups: list["OptionGroupPublicSchema"] | None = None
    variants: list["VariantPublicSchema"] | None = None


class ProductPublicListResponse(BaseModel):
    items: list[ProductPublicResponse]
    total: int
    page: int
    page_size: int


class CategoryPublicWithProductsResponse(BaseModel):
    category: CategoryPublicResponse
    products: ProductPublicListResponse


# ============================================================================
# Filter (public, faceted navigation) schemas
# ============================================================================


class FilterValueResponse(BaseModel):
    slug: str
    label: str
    count: int


class FilterParameterResponse(BaseModel):
    slug: str
    name: str
    type: str
    values: list[FilterValueResponse] = Field(default_factory=list)
    uom: UOMPublicResponse | None = None
    min: Decimal | None = None
    max: Decimal | None = None


class PriceRangeResponse(BaseModel):
    min: Decimal | None = None
    max: Decimal | None = None
    currency: str = "RUB"


class FiltersResponse(BaseModel):
    filters: list[FilterParameterResponse]
    price_range: PriceRangeResponse
    total_products: int


# ============================================================================
# SEO filter pages schemas
# ============================================================================


class SeoFilterItem(BaseModel):
    parameter_slug: str
    value_slug: str


class SeoFilterPage(BaseModel):
    category_slug: str | None = None
    filters: list[SeoFilterItem]
    product_count: int
    url_path: str


class SeoFilterPagesResponse(BaseModel):
    pages: list[SeoFilterPage]
    total: int


# ============================================================================
# Public variant schemas (referenced from ProductPublicDetailResponse)
# ============================================================================


class OptionValuePublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    slug: str
    color_hex: str | None = None
    image_url: str | None = None


class OptionGroupPublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    slug: str
    display_type: str
    values: list[OptionValuePublicSchema] = Field(default_factory=list)


class VariantPricePublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    price_type: str
    amount: Decimal
    currency: str


class VariantInclusionPublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str | None = None
    is_included: bool
    icon: str | None = None
    group: str | None = None


class VariantImagePublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    alt: str | None = None
    sort_order: int
    is_cover: bool


class VariantPublicSchema(BaseModel):
    id: UUID
    slug: str
    title: str
    sku: str
    description: str | None = None
    is_default: bool
    in_stock: bool
    sort_order: int
    prices: list[VariantPricePublicSchema] = Field(default_factory=list)
    options: dict[str, str] = Field(default_factory=dict)
    images: list[VariantImagePublicSchema] = Field(default_factory=list)
    inclusions: list[VariantInclusionPublicSchema] = Field(default_factory=list)


# Rebuild forward refs
ProductPublicDetailResponse.model_rebuild()
