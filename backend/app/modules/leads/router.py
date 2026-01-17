"""API routes for leads module."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, PublicTenantId
from app.core.logging import get_logger
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.notifications.service import NotificationService
from app.modules.tenants.models import Tenant

logger = get_logger(__name__)
from app.modules.leads.schemas import (
    InquiryAnalyticsSummary,
    InquiryCreatePublic,
    InquiryFormCreate,
    InquiryFormResponse,
    InquiryFormUpdate,
    InquiryListResponse,
    InquiryResponse,
    InquiryUpdate,
)
from app.modules.leads.service import InquiryFormService, InquiryService

router = APIRouter()


# ============================================================================
# Public Routes
# ============================================================================


@router.post(
    "/public/inquiries",
    response_model=InquiryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit inquiry",
    description="Submit an inquiry/lead from public form. Rate limited.",
    tags=["Public - Leads"],
)
async def create_inquiry_public(
    data: InquiryCreatePublic,
    request: Request,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> InquiryResponse:
    """Submit a public inquiry.

    This endpoint is rate-limited via RateLimitMiddleware (3 req/min per IP).
    Captures analytics data from the request.
    Sends notifications if configured in tenant settings.
    """
    # Get client IP
    ip_address = None
    if request.client:
        ip_address = request.client.host

    # Check for forwarded IP
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()

    service = InquiryService(db)
    inquiry = await service.create_from_public(tenant_id, data, ip_address)

    # Send notifications if enabled for this tenant
    await _send_inquiry_notification(db, tenant_id, inquiry)

    return InquiryResponse.model_validate(inquiry)


async def _send_inquiry_notification(
    db: AsyncSession,
    tenant_id: UUID,
    inquiry,
) -> None:
    """Send notification about new inquiry to configured channels.
    
    Notification is non-blocking - failures are logged but don't affect response.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    try:
        # Get tenant settings
        stmt = (
            select(Tenant)
            .options(selectinload(Tenant.settings))
            .where(Tenant.id == tenant_id)
        )
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant or not tenant.settings:
            return
        
        settings = tenant.settings
        
        # Check if notifications are enabled
        if not settings.notify_on_inquiry:
            return
        
        # Send notifications via configured channels
        notification_service = NotificationService()
        
        # Build source info
        source_parts = []
        if inquiry.utm_source:
            source_parts.append(f"utm_source={inquiry.utm_source}")
        if inquiry.page_url:
            source_parts.append(inquiry.page_url)
        source = ", ".join(source_parts) if source_parts else None
        
        results = await notification_service.notify_inquiry(
            notification_email=settings.inquiry_email,
            telegram_chat_id=settings.telegram_chat_id,
            inquiry_name=inquiry.name,
            inquiry_email=inquiry.email,
            inquiry_phone=inquiry.phone,
            inquiry_message=inquiry.message,
            inquiry_source=source,
        )
        
        logger.info(
            "inquiry_notification_sent",
            inquiry_id=str(inquiry.id),
            email_sent=results.get("email", False),
            telegram_sent=results.get("telegram", False),
        )
        
    except Exception as e:
        # Log error but don't fail the request
        logger.error(
            "inquiry_notification_failed",
            inquiry_id=str(inquiry.id),
            error=str(e),
        )


# ============================================================================
# Admin Routes - Inquiry Forms
# ============================================================================


@router.get(
    "/admin/inquiry-forms",
    response_model=list[InquiryFormResponse],
    summary="List inquiry forms",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("inquiries:read"))],
)
async def list_inquiry_forms(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[InquiryFormResponse]:
    """List all inquiry forms."""
    service = InquiryFormService(db)
    forms = await service.list_forms(tenant_id)
    return [InquiryFormResponse.model_validate(f) for f in forms]


@router.post(
    "/admin/inquiry-forms",
    response_model=InquiryFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create inquiry form",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def create_inquiry_form(
    data: InquiryFormCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> InquiryFormResponse:
    """Create a new inquiry form."""
    service = InquiryFormService(db)
    form = await service.create(tenant_id, data)
    return InquiryFormResponse.model_validate(form)


@router.get(
    "/admin/inquiry-forms/{form_id}",
    response_model=InquiryFormResponse,
    summary="Get inquiry form",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("inquiries:read"))],
)
async def get_inquiry_form(
    form_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> InquiryFormResponse:
    """Get inquiry form by ID."""
    service = InquiryFormService(db)
    form = await service.get_by_id(form_id, tenant_id)
    return InquiryFormResponse.model_validate(form)


@router.patch(
    "/admin/inquiry-forms/{form_id}",
    response_model=InquiryFormResponse,
    summary="Update inquiry form",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def update_inquiry_form(
    form_id: UUID,
    data: InquiryFormUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> InquiryFormResponse:
    """Update an inquiry form."""
    service = InquiryFormService(db)
    form = await service.update(form_id, tenant_id, data)
    return InquiryFormResponse.model_validate(form)


@router.delete(
    "/admin/inquiry-forms/{form_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete inquiry form",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def delete_inquiry_form(
    form_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an inquiry form."""
    service = InquiryFormService(db)
    await service.soft_delete(form_id, tenant_id)


# ============================================================================
# Admin Routes - Inquiries
# ============================================================================


@router.get(
    "/admin/inquiries",
    response_model=InquiryListResponse,
    summary="List inquiries",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("inquiries:read"))],
)
async def list_inquiries(
    pagination: Pagination,
    status: str | None = Query(default=None),
    form_id: UUID | None = Query(default=None, alias="formId"),
    assigned_to: UUID | None = Query(default=None, alias="assignedTo"),
    utm_source: str | None = Query(default=None, alias="utmSource"),
    search: str | None = Query(default=None, description="Search in name, email, company, phone"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> InquiryListResponse:
    """List inquiries with filters."""
    service = InquiryService(db)
    inquiries, total = await service.list_inquiries(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        form_id=form_id,
        assigned_to=assigned_to,
        utm_source=utm_source,
        search=search,
    )

    return InquiryListResponse(
        items=[InquiryResponse.model_validate(i) for i in inquiries],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/admin/inquiries/analytics",
    response_model=InquiryAnalyticsSummary,
    summary="Get inquiry analytics",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("inquiries:read"))],
)
async def get_inquiries_analytics(
    days: int = Query(default=30, ge=1, le=365),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> InquiryAnalyticsSummary:
    """Get analytics summary for inquiries."""
    service = InquiryService(db)
    summary = await service.get_analytics_summary(tenant_id, days)
    return InquiryAnalyticsSummary(**summary)


@router.get(
    "/admin/inquiries/{inquiry_id}",
    response_model=InquiryResponse,
    summary="Get inquiry",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("inquiries:read"))],
)
async def get_inquiry(
    inquiry_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> InquiryResponse:
    """Get inquiry by ID."""
    service = InquiryService(db)
    inquiry = await service.get_by_id(inquiry_id, tenant_id)
    return InquiryResponse.model_validate(inquiry)


@router.patch(
    "/admin/inquiries/{inquiry_id}",
    response_model=InquiryResponse,
    summary="Update inquiry",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("inquiries:update"))],
)
async def update_inquiry(
    inquiry_id: UUID,
    data: InquiryUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> InquiryResponse:
    """Update an inquiry (status, assignment, notes)."""
    service = InquiryService(db)
    inquiry = await service.update(inquiry_id, tenant_id, data)
    return InquiryResponse.model_validate(inquiry)


@router.delete(
    "/admin/inquiries/{inquiry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete inquiry",
    tags=["Admin - Leads"],
    dependencies=[Depends(PermissionChecker("inquiries:delete"))],
)
async def delete_inquiry(
    inquiry_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an inquiry."""
    service = InquiryService(db)
    await service.soft_delete(inquiry_id, tenant_id)

