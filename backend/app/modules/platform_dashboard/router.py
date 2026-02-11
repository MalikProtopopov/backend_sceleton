"""API routes for the platform owner dashboard.

All endpoints require superuser or platform_owner role.
No tenant_id scoping — data spans the entire platform.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_platform_owner
from app.modules.auth.models import AdminUser
from app.modules.platform_dashboard.schemas import (
    PlatformAlerts,
    PlatformOverview,
    PlatformTrends,
    TenantDetailStats,
    TenantTableResponse,
)
from app.modules.platform_dashboard.service import PlatformDashboardService

router = APIRouter(tags=["Platform Owner - Dashboard"])


@router.get(
    "/platform/overview",
    response_model=PlatformOverview,
    summary="Platform overview KPIs",
    description=(
        "Returns top-level summary cards: tenant counts, user counts, "
        "inquiry counts (this/prev month), and inactive-tenant count."
    ),
)
async def get_platform_overview(
    _user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> PlatformOverview:
    """Platform-level KPI cards."""
    service = PlatformDashboardService(db)
    return await service.get_overview()


@router.get(
    "/platform/tenants",
    response_model=TenantTableResponse,
    summary="Tenants table with metrics",
    description=(
        "Paginated list of all tenants with aggregated metrics: "
        "users, content, inquiries, last login, enabled features. "
        "Supports sorting and text search."
    ),
)
async def get_platform_tenants(
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=25, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(
        default="created_at",
        description="Sort column",
        pattern="^(name|slug|created_at|is_active|users_count|content_count|"
        "inquiries_total|inquiries_this_month|last_login_at|enabled_features_count)$",
    ),
    sort_dir: str = Query(
        default="desc",
        description="Sort direction",
        pattern="^(asc|desc)$",
    ),
    search: str | None = Query(
        default=None, max_length=200, description="Search in name, slug, domain"
    ),
    _user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantTableResponse:
    """Paginated tenants table with metrics."""
    service = PlatformDashboardService(db)
    return await service.get_tenants_table(
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search=search,
    )


@router.get(
    "/platform/tenants/{tenant_id}/details",
    response_model=TenantDetailStats,
    summary="Tenant drill-down statistics",
    description=(
        "Full statistics for a single tenant: content by status, "
        "inquiry analytics (UTM, device, geo, processing time), "
        "feature flags, users, recent audit activity."
    ),
)
async def get_tenant_details(
    tenant_id: UUID,
    _user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantDetailStats:
    """Full drill-down statistics for a single tenant."""
    service = PlatformDashboardService(db)
    return await service.get_tenant_details(tenant_id)


@router.get(
    "/platform/trends",
    response_model=PlatformTrends,
    summary="Platform trends (time series)",
    description=(
        "Time-series data for graphs: new tenants by month, "
        "new users by month, inquiries by day, logins by day, "
        "and inquiries broken down by top tenants."
    ),
)
async def get_platform_trends(
    days: int = Query(
        default=90, ge=7, le=365, description="Look-back period in days"
    ),
    _user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> PlatformTrends:
    """Time-series data for platform-level graphs."""
    service = PlatformDashboardService(db)
    return await service.get_trends(days)


@router.get(
    "/platform/alerts",
    response_model=PlatformAlerts,
    summary="Platform health alerts",
    description=(
        "Detects health issues across tenants: inactive tenants, "
        "stale inquiries, empty content, low feature adoption, "
        "high spam ratio, declining inquiry trends."
    ),
)
async def get_platform_alerts(
    _user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> PlatformAlerts:
    """Health alerts for the platform owner."""
    service = PlatformDashboardService(db)
    return await service.get_health_alerts()
