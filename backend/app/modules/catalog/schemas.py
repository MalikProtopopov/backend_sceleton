"""Pydantic schemas for catalog module."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    parent_id: UUID | None = None
    description: str | None = None
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
    description: str | None = None
    uom_id: UUID | None = None
    is_active: bool = True
    category_ids: list[UUID] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, max_length=500)
    brand: str | None = None
    model: str | None = None
    description: str | None = None
    uom_id: UUID | None = None
    is_active: bool | None = None
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


class ProductCharResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    value_text: str
    uom_id: UUID | None = None


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
    version: int
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageResponse] = Field(default_factory=list)


class ProductDetailResponse(ProductResponse):
    """Extended response with optionally loaded relations."""

    chars: list[ProductCharResponse] = Field(default_factory=list)
    aliases: list[ProductAliasResponse] = Field(default_factory=list)
    categories: list[ProductCategoryLinkResponse] = Field(default_factory=list)
    prices: list[ProductPriceResponse] = Field(default_factory=list)


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Product Char (EAV) bulk schemas
# ============================================================================


class ProductCharCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    value_text: str = Field(..., min_length=1)
    uom_id: UUID | None = None


class ProductCharUpdate(BaseModel):
    id: UUID
    name: str | None = Field(default=None, max_length=255)
    value_text: str | None = None
    uom_id: UUID | None = None


class ProductCharBulkUpdate(BaseModel):
    created: list[ProductCharCreate] | None = None
    updated: list[ProductCharUpdate] | None = None
    deleted: list[UUID] | None = None


class ProductCharBulkResponse(BaseModel):
    created: int
    updated: int
    deleted: int


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


class ProductCharPublicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    images: list[ProductImagePublicResponse] = Field(default_factory=list)
    chars: list[ProductCharPublicResponse] = Field(default_factory=list)
    categories: list[CategoryPublicResponse] = Field(default_factory=list)
    prices: list[ProductPricePublicResponse] = Field(default_factory=list)


class ProductPublicListResponse(BaseModel):
    items: list[ProductPublicResponse]
    total: int
    page: int
    page_size: int


class CategoryPublicWithProductsResponse(BaseModel):
    category: CategoryPublicResponse
    products: ProductPublicListResponse
