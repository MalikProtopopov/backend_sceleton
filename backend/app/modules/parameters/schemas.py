"""Pydantic schemas for parameters module."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Parameter Value Schemas
# ============================================================================


class ParameterValueCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=100)
    sort_order: int | None = None


class ParameterValueUpdate(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    code: str | None = Field(default=None, max_length=100)
    sort_order: int | None = None
    is_active: bool | None = None


class ParameterValueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parameter_id: UUID
    label: str
    slug: str
    code: str | None = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Parameter Schemas
# ============================================================================


class ParameterCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    value_type: str = Field(..., pattern="^(string|number|enum|bool|range)$")
    uom_id: UUID | None = None
    scope: str = Field(default="global", pattern="^(global|category)$")
    description: str | None = None
    constraints: dict | None = None
    is_filterable: bool = False
    is_required: bool = False
    sort_order: int = 0
    category_ids: list[UUID] | None = None
    values: list[ParameterValueCreate] | None = Field(
        default=None,
        description="Initial enum values (only for value_type='enum')",
    )


class ParameterUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    uom_id: UUID | None = None
    scope: str | None = Field(default=None, pattern="^(global|category)$")
    constraints: dict | None = None
    is_filterable: bool | None = None
    is_required: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ParameterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    value_type: str
    uom_id: UUID | None = None
    scope: str
    description: str | None = None
    constraints: dict | None = None
    is_filterable: bool
    is_required: bool
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    values: list[ParameterValueResponse] = Field(default_factory=list)
    category_ids: list[UUID] = Field(default_factory=list)


class ParameterListResponse(BaseModel):
    items: list[ParameterResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Parameter Category Schemas
# ============================================================================


class ParameterCategorySet(BaseModel):
    category_ids: list[UUID]


# ============================================================================
# Product Characteristic Schemas
# ============================================================================


class ProductCharacteristicCreate(BaseModel):
    parameter_id: UUID
    parameter_value_id: UUID | None = None
    value_text: str | None = None
    value_number: Decimal | None = None
    value_bool: bool | None = None
    uom_id: UUID | None = None
    source_type: str | None = Field(default="manual", pattern="^(manual|import|system)$")


class ProductCharacteristicBulkItem(BaseModel):
    parameter_id: UUID
    parameter_value_ids: list[UUID] | None = None
    value_text: str | None = None
    value_number: Decimal | None = None
    value_bool: bool | None = None
    uom_id: UUID | None = None


class ProductCharacteristicBulkCreate(BaseModel):
    characteristics: list[ProductCharacteristicBulkItem]


class ProductCharacteristicUpdate(BaseModel):
    parameter_value_id: UUID | None = None
    value_text: str | None = None
    value_number: Decimal | None = None
    value_bool: bool | None = None
    uom_id: UUID | None = None


class ProductCharacteristicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    parameter_id: UUID
    parameter_value_id: UUID | None = None
    value_text: str | None = None
    value_number: Decimal | None = None
    value_bool: bool | None = None
    uom_id: UUID | None = None
    source_type: str
    is_locked: bool
    created_at: datetime
    updated_at: datetime


class UOMBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    symbol: str | None = None


class ParameterValueBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    label: str
    slug: str


class ParameterBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    slug: str
    value_type: str
    is_filterable: bool
    uom: UOMBrief | None = None


class ProductCharacteristicDetailResponse(BaseModel):
    """Enriched characteristic with inline parameter/value names for admin UI."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    parameter_id: UUID
    parameter_value_id: UUID | None = None
    value_text: str | None = None
    value_number: Decimal | None = None
    value_bool: bool | None = None
    uom_id: UUID | None = None
    source_type: str
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    parameter: ParameterBrief
    parameter_value: ParameterValueBrief | None = None


class ProductCharacteristicBulkResponse(BaseModel):
    created: int
    updated: int
    deleted: int
