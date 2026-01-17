"""API routes for export module."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.export.schemas import ExportFormat, ExportResourceType
from app.modules.export.service import ExportService

router = APIRouter(tags=["Admin - Export"])


@router.get(
    "/export",
    summary="Export data",
    dependencies=[Depends(PermissionChecker("export:read"))],
)
async def export_data(
    resource_type: ExportResourceType = Query(..., alias="resourceType"),
    format: ExportFormat = Query(default=ExportFormat.CSV),
    status: str | None = Query(default=None),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    columns: str | None = Query(default=None, description="Comma-separated list of columns"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Export data to CSV or JSON format.

    Supported resource types:
    - inquiries: Lead data with contact info and UTM tracking
    - team: Employee/team member data
    - seo_routes: SEO metadata by URL
    - audit_logs: System audit trail

    Query parameters:
    - resourceType: Type of data to export (required)
    - format: Output format (csv or json, default: csv)
    - status: Filter by status (for inquiries)
    - dateFrom: Filter by start date (ISO format)
    - dateTo: Filter by end date (ISO format)
    - columns: Comma-separated list of columns to include
    """
    service = ExportService(db)

    # Parse columns if provided
    column_list = None
    if columns:
        column_list = [c.strip() for c in columns.split(",")]

    content, content_type, filename = await service.export_data(
        tenant_id=tenant_id,
        resource_type=resource_type,
        format=format,
        status=status,
        date_from=date_from,
        date_to=date_to,
        columns=column_list,
    )

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

