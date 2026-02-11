"""Pydantic schemas for the platform owner dashboard.

All responses aggregate data across tenants — intended for
superuser / platform_owner role only.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Platform Overview (top-level cards)
# ============================================================================


class PlatformOverview(BaseModel):
    """High-level platform KPIs shown as summary cards."""

    # Tenants
    total_tenants: int = 0
    active_tenants: int = 0
    inactive_tenants: int = 0

    # Users
    total_users: int = 0
    active_users: int = 0

    # Inquiries
    total_inquiries: int = 0
    inquiries_this_month: int = 0
    inquiries_prev_month: int = 0

    # Health
    inactive_tenants_30d: int = Field(
        default=0,
        description="Tenants where no user logged in for >30 days",
    )


# ============================================================================
# Tenants Table
# ============================================================================


class TenantRow(BaseModel):
    """Single row in the platform tenants table."""

    id: UUID
    name: str
    slug: str
    domain: str | None = None
    is_active: bool
    created_at: datetime

    # Users
    users_count: int = 0
    active_users_count: int = 0

    # Content (published totals)
    content_count: int = Field(
        default=0, description="Total published content items across all types"
    )
    articles_count: int = 0
    cases_count: int = 0
    services_count: int = 0

    # Inquiries
    inquiries_total: int = 0
    inquiries_this_month: int = 0
    inquiries_new: int = Field(
        default=0, description="Unprocessed inquiries (status=new)"
    )

    # Activity
    last_login_at: datetime | None = Field(
        default=None, description="Most recent login across all tenant users"
    )

    # Features
    enabled_features_count: int = 0
    enabled_features: list[str] = Field(default_factory=list)


class TenantTableResponse(BaseModel):
    """Paginated list of tenants with metrics."""

    items: list[TenantRow]
    total: int
    page: int
    per_page: int
    pages: int


# ============================================================================
# Tenant Detail (drill-down)
# ============================================================================


class ContentByStatus(BaseModel):
    """Content breakdown by publication status."""

    published: int = 0
    draft: int = 0
    archived: int = 0


class ReviewByStatus(BaseModel):
    """Review breakdown by moderation status."""

    pending: int = 0
    approved: int = 0
    rejected: int = 0


class ContentBreakdown(BaseModel):
    """Full content breakdown for a tenant."""

    articles: ContentByStatus = Field(default_factory=ContentByStatus)
    cases: ContentByStatus = Field(default_factory=ContentByStatus)
    documents: ContentByStatus = Field(default_factory=ContentByStatus)
    services: int = Field(default=0, description="Published services")
    services_total: int = 0
    employees: int = Field(default=0, description="Published employees")
    employees_total: int = 0
    faqs: int = Field(default=0, description="Published FAQs")
    faqs_total: int = 0
    reviews: ReviewByStatus = Field(default_factory=ReviewByStatus)


class InquiryBreakdown(BaseModel):
    """Inquiry analytics for a tenant."""

    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_utm_source: dict[str, int] = Field(default_factory=dict)
    by_device_type: dict[str, int] = Field(default_factory=dict)
    by_country_top10: list[dict[str, int | str]] = Field(default_factory=list)
    top_pages: list[dict[str, int | str]] = Field(default_factory=list)
    avg_processing_hours: float | None = Field(
        default=None,
        description="Average hours from creation to first contact",
    )


class FeatureFlagInfo(BaseModel):
    """Feature flag state."""

    feature_name: str
    enabled: bool


class TenantUserInfo(BaseModel):
    """User summary inside a tenant."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    role_name: str | None = None
    last_login_at: datetime | None = None


class AuditEntry(BaseModel):
    """Single audit log entry."""

    id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    user_email: str | None = None
    created_at: datetime


class TenantDetailStats(BaseModel):
    """Full drill-down statistics for a single tenant."""

    # Tenant info
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    is_active: bool

    # Breakdowns
    content: ContentBreakdown = Field(default_factory=ContentBreakdown)
    inquiries: InquiryBreakdown = Field(default_factory=InquiryBreakdown)

    # Features
    feature_flags: list[FeatureFlagInfo] = Field(default_factory=list)

    # Users
    users: list[TenantUserInfo] = Field(default_factory=list)

    # Recent activity
    recent_activity: list[AuditEntry] = Field(default_factory=list)


# ============================================================================
# Trends (time-series)
# ============================================================================


class TrendPoint(BaseModel):
    """Single data point in a time series."""

    date: str = Field(description="ISO date string (YYYY-MM-DD or YYYY-MM)")
    value: int = 0


class TenantTrendSeries(BaseModel):
    """Inquiry trend for a specific tenant."""

    tenant_id: UUID
    tenant_name: str
    data: list[TrendPoint] = Field(default_factory=list)


class PlatformTrends(BaseModel):
    """Time-series data for platform-level graphs."""

    new_tenants_by_month: list[TrendPoint] = Field(default_factory=list)
    new_users_by_month: list[TrendPoint] = Field(default_factory=list)
    inquiries_by_day: list[TrendPoint] = Field(default_factory=list)
    logins_by_day: list[TrendPoint] = Field(default_factory=list)
    inquiries_by_tenant: list[TenantTrendSeries] = Field(default_factory=list)


# ============================================================================
# Health Alerts
# ============================================================================


class HealthAlert(BaseModel):
    """A single health alert for the platform owner."""

    type: str = Field(description="Alert type key, e.g. 'inactive_tenant'")
    severity: str = Field(description="critical | warning | info")
    tenant_id: UUID | None = None
    tenant_name: str | None = None
    message: str
    details: dict | None = None


class AlertSummary(BaseModel):
    """Counts per severity."""

    critical: int = 0
    warning: int = 0
    info: int = 0


class PlatformAlerts(BaseModel):
    """Health alerts response."""

    alerts: list[HealthAlert] = Field(default_factory=list)
    summary: AlertSummary = Field(default_factory=AlertSummary)
