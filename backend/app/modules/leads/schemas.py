"""Pydantic schemas for leads module."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InquiryStatus(str, Enum):
    """Inquiry processing status."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    CONTACTED = "contacted"
    COMPLETED = "completed"
    SPAM = "spam"


# ============================================================================
# Inquiry Form Schemas
# ============================================================================


class InquiryFormBase(BaseModel):
    """Base schema for inquiry form."""

    slug: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True
    notification_email: str | None = Field(default=None, max_length=255)
    success_message: dict | None = None
    fields_config: dict | None = None
    sort_order: int = 0


class InquiryFormCreate(InquiryFormBase):
    """Schema for creating inquiry form."""

    pass


class InquiryFormUpdate(BaseModel):
    """Schema for updating inquiry form."""

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    is_active: bool | None = None
    notification_email: str | None = None
    success_message: dict | None = None
    fields_config: dict | None = None
    sort_order: int | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class InquiryFormResponse(InquiryFormBase):
    """Schema for inquiry form response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Inquiry (Lead) Schemas
# ============================================================================


class InquiryAnalytics(BaseModel):
    """Analytics data captured with inquiry."""

    # UTM
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None

    # Referrer
    referrer_url: str | None = Field(default=None, max_length=2000)

    # Page context
    source_url: str | None = Field(default=None, max_length=2000)
    page_path: str | None = Field(default=None, max_length=500)
    page_title: str | None = Field(default=None, max_length=500)

    # Device
    user_agent: str | None = Field(default=None, max_length=500)
    device_type: str | None = Field(default=None, max_length=20)
    browser: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=100)
    screen_resolution: str | None = Field(default=None, max_length=20)

    # Session
    session_id: str | None = Field(default=None, max_length=100)
    session_page_views: int | None = None
    time_on_page: int | None = None


class InquiryCreatePublic(BaseModel):
    """Schema for creating inquiry from public form."""

    # Form identifier
    form_slug: str | None = Field(default=None, max_length=100)

    # Contact info (required)
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=255)

    # Message
    message: str | None = None

    # Service context
    service_id: UUID | None = None

    # Analytics
    analytics: InquiryAnalytics | None = None

    # Custom fields
    custom_fields: dict | None = None


class InquiryUpdate(BaseModel):
    """Schema for updating inquiry (admin)."""

    status: InquiryStatus | None = None
    assigned_to: UUID | None = None
    notes: str | None = None


class InquiryResponse(BaseModel):
    """Schema for inquiry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    form_id: UUID | None = None
    status: str

    # Contact info
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    message: str | None = None

    # Service
    service_id: UUID | None = None

    # UTM
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None

    # Source
    referrer_url: str | None = None
    source_url: str | None = None
    page_path: str | None = None
    page_title: str | None = None

    # Device
    device_type: str | None = None
    browser: str | None = None
    os: str | None = None
    ip_address: str | None = None
    country: str | None = None
    city: str | None = None

    # Session
    session_id: str | None = None
    session_page_views: int | None = None
    time_on_page: int | None = None

    # Processing
    assigned_to: UUID | None = None
    notes: str | None = None
    contacted_at: datetime | None = None
    notification_sent: bool = False

    # Custom
    custom_fields: dict | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime


class InquiryListResponse(BaseModel):
    """Schema for inquiry list response."""

    items: list[InquiryResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Analytics Summary Schemas
# ============================================================================


class InquiryAnalyticsSummary(BaseModel):
    """Summary analytics for inquiries."""

    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_utm_source: dict[str, int] = Field(default_factory=dict)
    by_device_type: dict[str, int] = Field(default_factory=dict)
    by_day: list[dict] = Field(default_factory=list)

