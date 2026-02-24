"""Pydantic schemas for leads module."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class InquiryStatus(str, Enum):
    """Inquiry processing status."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    CONTACTED = "contacted"
    COMPLETED = "completed"
    SPAM = "spam"
    CANCELLED = "cancelled"


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


# Allowed form_slug values for short / full brief
FORM_SLUG_QUICK = "quick"
FORM_SLUG_MVP_BRIEF = "mvp-brief"

# Human-readable labels for custom_fields keys (used in admin UI and Telegram)
CUSTOM_FIELDS_LABELS: dict[str, str] = {
    "idea": "Идея / описание проекта",
    "market": "Рынок",
    "audience": "Описание аудитории",
    "audienceSize": "Размер аудитории",
    "aiRequired": "Нужен ли AI/ML",
    "appTypes": "Типы приложения",
    "integrations": "Интеграции",
    "budget": "Бюджет",
    "urgency": "Срочность",
    "source": "Откуда узнали",
    "telegram": "Telegram",
    "consent": "Согласие на обработку ПД",
}


class InquiryCreatePublic(BaseModel):
    """Schema for creating inquiry from public form.

    Supports two form types:
    - quick: name, email, message (required), phone?, telegram?, consent
    - mvp-brief: name, email, idea (required), plus idea/market/audience/... in custom_fields
    """

    # Form identifier: quick | mvp-brief (or other slugs from inquiry_forms)
    form_slug: str | None = Field(default=None, max_length=100)

    # Contact info (required)
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=255)

    # Message (required for form_slug=quick)
    message: str | None = None

    # Quick form: telegram; consent required (true)
    telegram: str | None = Field(default=None, max_length=255)
    consent: bool | None = None

    # Context: service or product the inquiry is about
    service_id: UUID | None = None
    product_id: UUID | None = None

    # Analytics
    analytics: InquiryAnalytics | None = None

    # Custom fields (merged with mvp-brief top-level fields when saving)
    custom_fields: dict | None = None

    # MVP brief top-level fields (stored in custom_fields; idea also used as message)
    idea: str | None = Field(default=None, max_length=2000)
    market: str | None = Field(default=None, max_length=100)
    audience: str | None = Field(default=None, max_length=1000)
    audienceSize: str | None = Field(default=None, max_length=50)
    aiRequired: str | None = Field(default=None, max_length=50)
    appTypes: list[str] | None = None
    integrations: str | None = Field(default=None, max_length=500)
    budget: str | None = Field(default=None, max_length=50)
    urgency: str | None = Field(default=None, max_length=50)
    source: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_form_fields(self) -> "InquiryCreatePublic":
        """For form_slug=quick require message; for mvp-brief require idea."""
        if self.form_slug == FORM_SLUG_QUICK and not (self.message or "").strip():
            raise ValueError("message is required for form_slug=quick")
        if self.form_slug == FORM_SLUG_MVP_BRIEF and not (self.idea or "").strip():
            raise ValueError("idea is required for form_slug=mvp-brief")
        return self


class InquiryUpdate(BaseModel):
    """Schema for updating inquiry (admin)."""

    status: InquiryStatus | None = None
    assigned_to: UUID | None = None
    notes: str | None = None


class InquiryProductBrief(BaseModel):
    """Brief product info embedded in inquiry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    sku: str
    name: str | None = None  # product title


class InquiryResponse(BaseModel):
    """Schema for inquiry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    form_id: UUID | None = None
    form_slug: str | None = None  # slug of linked form (quick, mvp-brief, etc.)
    status: str

    # Contact info
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    message: str | None = None

    # Context
    service_id: UUID | None = None
    product_id: UUID | None = None
    product: InquiryProductBrief | None = None

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
    custom_fields_display: list[dict] | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def build_custom_fields_display(self) -> "InquiryResponse":
        """Build human-readable display list from custom_fields."""
        if not self.custom_fields:
            return self
        display: list[dict[str, Any]] = []
        for key, value in self.custom_fields.items():
            if value is None:
                continue
            label = CUSTOM_FIELDS_LABELS.get(key, key)
            # Format list values (e.g. appTypes)
            if isinstance(value, list):
                display_value = ", ".join(str(v) for v in value)
            elif isinstance(value, bool):
                display_value = "Да" if value else "Нет"
            else:
                display_value = str(value)
            display.append({"key": key, "label": label, "value": display_value})
        self.custom_fields_display = display if display else None
        return self


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

