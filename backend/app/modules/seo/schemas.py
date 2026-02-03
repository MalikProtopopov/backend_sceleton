"""Pydantic schemas for SEO module."""

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# SEO Route Schemas
# ============================================================================


class SEORouteBase(BaseModel):
    """Base schema for SEO route."""

    path: str = Field(..., min_length=1, max_length=500)
    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, max_length=70)
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)
    meta_keywords: str | None = Field(default=None, max_length=255)
    og_image: str | None = Field(default=None, max_length=500)
    canonical_url: str | None = Field(default=None, max_length=500)
    robots_index: bool = True
    robots_follow: bool = True
    structured_data: str | None = None
    sitemap_priority: float | None = Field(default=0.5, ge=0.0, le=1.0)
    sitemap_changefreq: str | None = Field(default="weekly", max_length=20)
    include_in_sitemap: bool = True


class SEORouteCreate(SEORouteBase):
    """Schema for creating SEO route."""

    pass


class SEORouteUpdate(BaseModel):
    """Schema for updating SEO route."""

    title: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    og_image: str | None = None
    canonical_url: str | None = None
    robots_index: bool | None = None
    robots_follow: bool | None = None
    structured_data: str | None = None
    sitemap_priority: float | None = Field(default=None, ge=0.0, le=1.0)
    sitemap_changefreq: str | None = None
    include_in_sitemap: bool | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class SEORouteResponse(SEORouteBase):
    """Schema for SEO route response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    version: int
    robots_meta: str
    created_at: datetime
    updated_at: datetime


class SEOMetaResponse(BaseModel):
    """Schema for public SEO meta response."""

    title: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    og_image: str | None = None
    canonical_url: str | None = None
    robots: str = "index, follow"
    structured_data: str | None = None
    normalized_path: str | None = None
    
    @field_validator("structured_data")
    @classmethod
    def validate_structured_data(cls, v: str | None) -> str | None:
        """Validate that structured_data is valid JSON."""
        if v is not None:
            try:
                json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(f"structured_data must be valid JSON: {e}")
        return v


# ============================================================================
# Redirect Schemas
# ============================================================================


class RedirectBase(BaseModel):
    """Base schema for redirect."""

    source_path: str = Field(..., min_length=1, max_length=500)
    target_url: str = Field(..., min_length=1, max_length=2000)
    redirect_type: int = Field(default=301)
    is_active: bool = True

    @field_validator("redirect_type")
    @classmethod
    def validate_redirect_type(cls, v: int) -> int:
        if v not in (301, 302, 307, 308):
            raise ValueError("Redirect type must be 301, 302, 307, or 308")
        return v


class RedirectCreate(RedirectBase):
    """Schema for creating redirect."""

    pass


class RedirectUpdate(BaseModel):
    """Schema for updating redirect."""

    target_url: str | None = Field(default=None, max_length=2000)
    redirect_type: int | None = None
    is_active: bool | None = None

    @field_validator("redirect_type")
    @classmethod
    def validate_redirect_type(cls, v: int | None) -> int | None:
        if v is not None and v not in (301, 302, 307, 308):
            raise ValueError("Redirect type must be 301, 302, 307, or 308")
        return v


class RedirectResponse(RedirectBase):
    """Schema for redirect response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    hit_count: int
    created_at: datetime
    updated_at: datetime


class RedirectListResponse(BaseModel):
    """Schema for redirect list response."""

    items: list[RedirectResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Sitemap Schemas
# ============================================================================


class SitemapURL(BaseModel):
    """Single URL entry for sitemap."""

    loc: str
    lastmod: str | None = None
    changefreq: str | None = None
    priority: float | None = None


class RobotsResponse(BaseModel):
    """Robots.txt content."""

    content: str


# ============================================================================
# Redirect Export Schemas (for edge/proxy consumption)
# ============================================================================


class RedirectExportItem(BaseModel):
    """Single redirect item for export."""

    source_path: str
    target_url: str
    type: int = Field(alias="redirect_type")
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)


class RedirectExportResponse(BaseModel):
    """Response schema for public redirects export endpoint."""

    generated_at: datetime
    etag: str
    redirects: list[RedirectExportItem]


# ============================================================================
# Sitemap Metadata Schema
# ============================================================================


class SitemapMetadata(BaseModel):
    """Metadata for sitemap caching."""

    last_modified: datetime | None = None
    total_count: int = 0
    etag: str | None = None


# ============================================================================
# Admin Revalidation Schemas
# ============================================================================


class RevalidateRequest(BaseModel):
    """Request schema for cache revalidation."""

    targets: list[str] = Field(
        default=["all"],
        description="Targets to revalidate: 'sitemap', 'robots', 'redirects', 'meta', 'all'",
    )
    notify_frontend: bool = Field(
        default=False,
        description="Whether to notify frontend of revalidation",
    )
    
    @field_validator("targets")
    @classmethod
    def validate_targets(cls, v: list[str]) -> list[str]:
        """Validate revalidation targets."""
        valid_targets = {"sitemap", "robots", "redirects", "meta", "all"}
        for target in v:
            if target not in valid_targets:
                raise ValueError(f"Invalid target '{target}'. Valid targets: {', '.join(valid_targets)}")
        return v


class RevalidateResponse(BaseModel):
    """Response schema for cache revalidation."""

    success: bool = True
    message: str = "Cache revalidation triggered"
    targets: list[str]
    timestamp: datetime

