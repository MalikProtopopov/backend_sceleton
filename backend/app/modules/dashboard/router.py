"""API routes for dashboard module."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.dashboard.schemas import DashboardResponse
from app.modules.dashboard.service import DashboardService

router = APIRouter(tags=["Admin - Dashboard"])


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get dashboard statistics",
    dependencies=[Depends(PermissionChecker("dashboard:read"))],
)
async def get_dashboard(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    """Get dashboard statistics for the admin panel.

    Returns:
    - Content summary (articles, cases, team, services, FAQs, reviews counts)
    - Inquiry summary (total, by status, this month)
    - Content breakdown by status (published, draft, archived)
    - Recent activity (from audit logs - empty until audit module implemented)
    """
    service = DashboardService(db)
    return await service.get_dashboard(tenant_id)

