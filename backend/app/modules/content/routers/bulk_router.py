"""Bulk operations routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.content.schemas import BulkOperationRequest, BulkOperationResponse
from app.modules.content.service import BulkOperationService

router = APIRouter()


# ============================================================================
# Admin Routes - Bulk Operations
# ============================================================================


@router.post(
    "/admin/bulk",
    response_model=BulkOperationResponse,
    summary="Bulk operations",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("content:bulk"))],
)
async def bulk_operation(
    data: BulkOperationRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkOperationResponse:
    """Execute bulk operations on content.

    Supported resource types:
    - articles: Publish, unpublish, archive, delete
    - cases: Publish, unpublish, archive, delete
    - faq: Publish, unpublish, delete
    - reviews: Publish (approve), unpublish (reject), delete

    Items are processed synchronously for < 100 items.
    """
    service = BulkOperationService(db)
    summary = await service.execute(tenant_id, data)

    return BulkOperationResponse(
        job_id=None,
        status="completed",
        summary=summary,
    )
