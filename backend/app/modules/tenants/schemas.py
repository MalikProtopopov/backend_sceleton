"""Pydantic schemas for tenants module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Feature Flag Schemas
# ============================================================================


class FeatureFlagBase(BaseModel):
    """Base feature flag schema."""

    feature_name: str = Field(..., min_length=2, max_length=100)
    enabled: bool = False
    description: str | None = None


class FeatureFlagCreate(FeatureFlagBase):
    """Schema for creating a feature flag."""

    pass


class FeatureFlagUpdate(BaseModel):
    """Schema for updating a feature flag."""

    enabled: bool


class FeatureFlagResponse(FeatureFlagBase):
    """Schema for feature flag response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class FeatureFlagsListResponse(BaseModel):
    """Schema for list of feature flags."""

    items: list[FeatureFlagResponse]
    available_features: dict[str, str]


# ============================================================================
# Tenant Settings Schemas
# ============================================================================


class TenantSettingsBase(BaseModel):
    """Base tenant settings schema."""

    default_locale: str = Field(default="ru", min_length=2, max_length=5)
    timezone: str = Field(default="Europe/Moscow", max_length=50)
    date_format: str = Field(default="DD.MM.YYYY", max_length=20)
    time_format: str = Field(default="HH:mm", max_length=10)
    notify_on_inquiry: bool = True
    inquiry_email: str | None = None
    telegram_chat_id: str | None = None
    default_og_image: str | None = None
    ga_tracking_id: str | None = None
    ym_counter_id: str | None = None


class TenantSettingsUpdate(TenantSettingsBase):
    """Schema for updating tenant settings."""

    pass


class TenantSettingsResponse(TenantSettingsBase):
    """Schema for tenant settings response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Tenant Schemas
# ============================================================================


class TenantBase(BaseModel):
    """Base tenant schema."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    domain: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    primary_color: str | None = Field(default=None, max_length=7)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is lowercase and URL-friendly."""
        import re

        if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", v):
            raise ValueError("Slug must contain only lowercase letters, numbers, and hyphens")
        return v

    @field_validator("primary_color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        """Validate hex color format."""
        import re

        if v is not None and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be in #RRGGBB format")
        return v


class TenantCreate(TenantBase):
    """Schema for creating a tenant.
    
    Note: logo_url is managed via POST /tenants/{id}/logo endpoint.
    """

    pass


class TenantUpdate(BaseModel):
    """Schema for updating a tenant.
    
    Note: logo_url is managed via POST/DELETE /tenants/{id}/logo endpoints.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    primary_color: str | None = Field(default=None, max_length=7)
    version: int = Field(..., description="Current version for optimistic locking")

    @field_validator("primary_color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        """Validate hex color format."""
        import re

        if v is not None and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be in #RRGGBB format")
        return v


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    logo_url: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    settings: TenantSettingsResponse | None = None


class TenantListResponse(BaseModel):
    """Schema for tenant list response."""

    items: list[TenantResponse]
    total: int
    page: int
    page_size: int

