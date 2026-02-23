"""Pydantic schemas for tenants module."""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


# ============================================================================
# Tenant Domain Schemas
# ============================================================================


_DOMAIN_RE = re.compile(
    r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z0-9-]{1,63})*\.[A-Za-z]{2,}$"
)


class TenantDomainCreate(BaseModel):
    """Schema for adding a domain to a tenant."""

    domain: str = Field(..., min_length=4, max_length=255, description="FQDN, e.g. admin.client.com")
    is_primary: bool = Field(default=False, description="Mark as primary domain for this tenant")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not _DOMAIN_RE.match(v):
            raise ValueError("Invalid domain format. Expected FQDN like admin.client.com")
        return v


class TenantDomainUpdate(BaseModel):
    """Schema for updating a tenant domain."""

    is_primary: bool | None = None
    ssl_status: Literal["pending", "active", "error"] | None = None


class TenantDomainResponse(BaseModel):
    """Schema for tenant domain response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    domain: str
    is_primary: bool
    ssl_status: str
    created_at: datetime
    updated_at: datetime


class TenantDomainListResponse(BaseModel):
    """Schema for list of tenant domains."""

    items: list[TenantDomainResponse]
    total: int


class TenantByDomainResponse(BaseModel):
    """Public response when resolving a tenant by hostname.

    Used by the admin SPA at startup: GET /public/tenants/by-domain/{domain}
    """

    tenant_id: UUID
    slug: str
    name: str
    logo_url: str | None = None
    primary_color: str | None = None
    site_url: str | None = None


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
    available_features: dict[str, dict[str, str]]


# ============================================================================
# Tenant Settings Schemas
# ============================================================================


class SitemapStaticPage(BaseModel):
    """Schema for static page in sitemap configuration."""
    
    path: str = Field(..., min_length=1, max_length=500)
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    changefreq: str = Field(default="weekly", max_length=20)


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
    ym_counter_id: str | None = Field(
        default=None,
        max_length=5000,
        description="Yandex.Metrika counter ID or full embed code",
    )
    
    # SEO domain validation
    allowed_domains: list[str] | None = Field(
        default=None,
        description="List of allowed domains for sitemap/robots base_url validation",
    )
    site_url: str | None = Field(
        default=None,
        max_length=500,
        description=(
            "Frontend base URL (e.g. https://mediann.dev). "
            "Used for SEO (sitemap, robots.txt) and automatically added to allowed CORS origins."
        ),
    )
    
    # SEO sitemap configuration
    sitemap_static_pages: list[SitemapStaticPage] | None = Field(
        default=None,
        description="Static pages for sitemap",
    )
    
    # SEO robots.txt customization
    robots_txt_custom_rules: str | None = Field(
        default=None,
        max_length=5000,
        description="Custom rules to append to robots.txt",
    )
    
    # IndexNow integration
    indexnow_key: str | None = Field(
        default=None,
        max_length=64,
        description="IndexNow API key for search engine notification",
    )
    indexnow_enabled: bool = Field(
        default=False,
        description="Enable IndexNow URL submission",
    )
    
    # AI discovery (llms.txt)
    llms_txt_enabled: bool = Field(
        default=False,
        description="Enable llms.txt generation for AI discovery",
    )
    llms_txt_custom_content: str | None = Field(
        default=None,
        max_length=10000,
        description="Custom content to include in llms.txt",
    )

    # Webmaster verification codes
    yandex_verification_code: str | None = Field(
        default=None,
        max_length=255,
        description="Yandex.Webmaster verification filename without .html (e.g. 'yandex_821edd51f146c052')",
        examples=["yandex_821edd51f146c052"],
    )
    google_verification_code: str | None = Field(
        default=None,
        max_length=255,
        description="Google Search Console verification filename without .html (e.g. 'google1234567890abcdef')",
        examples=["google1234567890abcdef"],
    )
    google_verification_meta: str | None = Field(
        default=None,
        max_length=500,
        description="Google Search Console meta tag content value (alternative to file method)",
        examples=["1234567890abcdef1234567890abcdef"],
    )

    # Email / SMTP configuration (per-tenant)
    email_provider: Literal["smtp", "sendgrid", "mailgun", "console"] | None = Field(
        default=None,
        description="Email provider for this tenant. NULL = use global default.",
    )
    email_from_address: str | None = Field(
        default=None,
        max_length=255,
        description="Sender email address for this tenant",
    )
    email_from_name: str | None = Field(
        default=None,
        max_length=255,
        description="Sender display name for this tenant",
    )
    smtp_host: str | None = Field(
        default=None,
        max_length=255,
        description="SMTP server host (e.g. smtp.gmail.com)",
    )
    smtp_port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
        description="SMTP server port (587=STARTTLS, 465=SSL)",
    )
    smtp_user: str | None = Field(
        default=None,
        max_length=255,
        description="SMTP authentication username",
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="Use STARTTLS for SMTP connection",
    )

    @field_validator("site_url")
    @classmethod
    def validate_site_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().rstrip("/")
        if not v:
            return None
        if not re.match(r"^https?://[a-zA-Z0-9]", v):
            raise ValueError(
                "site_url must be a valid URL starting with http:// or https://"
            )
        return v

    @field_validator("yandex_verification_code")
    @classmethod
    def validate_yandex_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^yandex_[a-f0-9]+$", v):
            raise ValueError(
                "Invalid Yandex verification code format. "
                "Expected: yandex_[hex], e.g. yandex_821edd51f146c052"
            )
        return v

    @field_validator("google_verification_code")
    @classmethod
    def validate_google_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not re.match(r"^google[a-f0-9]+$", v):
            raise ValueError(
                "Invalid Google verification code format. "
                "Expected: google[hex], e.g. google1234567890abcdef"
            )
        return v


class TenantSettingsUpdate(TenantSettingsBase):
    """Schema for updating tenant settings.

    smtp_password and email_api_key are write-only fields.
    They are encrypted before storage and never returned in responses.
    Pass null/empty to clear, or omit to keep unchanged.
    """

    smtp_password: str | None = Field(
        default=None,
        max_length=500,
        description="SMTP password (write-only, encrypted at rest). Pass null to clear.",
    )
    email_api_key: str | None = Field(
        default=None,
        max_length=500,
        description="SendGrid/Mailgun API key (write-only, encrypted at rest). Pass null to clear.",
    )


class TenantSettingsResponse(TenantSettingsBase):
    """Schema for tenant settings response.

    Sensitive fields (smtp_password, email_api_key) are masked.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    # Masked secrets — show whether a value is configured, not the actual value
    smtp_password_configured: bool = Field(
        default=False,
        description="Whether SMTP password is configured (actual value is never returned)",
    )
    email_api_key_configured: bool = Field(
        default=False,
        description="Whether email API key is configured (actual value is never returned)",
    )

    @model_validator(mode="before")
    @classmethod
    def compute_secret_flags(cls, data):
        """Compute *_configured flags from encrypted DB fields."""
        if hasattr(data, "__dict__"):
            # ORM model — access attributes
            obj = data
            smtp_enc = getattr(obj, "smtp_password_encrypted", None)
            api_enc = getattr(obj, "email_api_key_encrypted", None)
            # Pydantic v2 from_attributes: we must inject into a dict copy
            d = {}
            for field_name in cls.model_fields:
                if hasattr(obj, field_name):
                    d[field_name] = getattr(obj, field_name)
            d["smtp_password_configured"] = bool(smtp_enc)
            d["email_api_key_configured"] = bool(api_enc)
            return d
        # dict input (e.g., from .model_dump())
        if isinstance(data, dict):
            data["smtp_password_configured"] = bool(data.get("smtp_password_encrypted"))
            data["email_api_key_configured"] = bool(data.get("email_api_key_encrypted"))
        return data


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
    users_count: int = Field(default=0, description="Number of active users in this tenant")
    created_at: datetime
    updated_at: datetime
    settings: TenantSettingsResponse | None = None


class TenantListResponse(BaseModel):
    """Schema for tenant list response."""

    items: list[TenantResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Public Tenant Schema
# ============================================================================


class TenantPublicResponse(BaseModel):
    """Public tenant information (safe for frontend).
    
    This schema exposes only non-sensitive tenant data for public API.
    Does not include: domain, contact_email, contact_phone, extra_data, settings, feature_flags.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    logo_url: str | None = None
    primary_color: str | None = None
    site_url: str | None = Field(
        default=None,
        description="Frontend base URL for the tenant site (e.g. https://mediann.dev). "
        "Used by client frontend for sitemap proxying, canonical URLs, etc.",
    )


class TenantAnalyticsPublic(BaseModel):
    """Public analytics and verification scripts for frontend.
    
    ga_tracking_id: Google Analytics measurement ID (e.g. G-XXXXXXXXXX).
    ym_counter_id: Yandex.Metrika counter ID (e.g. 92699637) or full embed HTML snippet.
    google_verification_meta: Google Search Console meta tag content value.
    """

    ga_tracking_id: str | None = None
    ym_counter_id: str | None = None
    google_verification_meta: str | None = None


# ============================================================================
# Email Test / Email Log Schemas
# ============================================================================


class EmailTestRequest(BaseModel):
    """Request to send a test email using tenant's email configuration."""

    to_email: EmailStr = Field(..., description="Recipient email address for the test")


class EmailTestResponse(BaseModel):
    """Response from the email test endpoint."""

    success: bool
    provider: str | None = None
    error: str | None = None


class EmailLogResponse(BaseModel):
    """Schema for email log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    to_email: str
    subject: str
    email_type: str
    provider: str
    status: str
    error_message: str | None = None
    created_at: datetime


class EmailLogListResponse(BaseModel):
    """Schema for paginated email logs."""

    items: list[EmailLogResponse]
    total: int
    page: int
    page_size: int

