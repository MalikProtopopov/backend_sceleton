"""API routes for leads module."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, PublicTenantId
from app.core.logging import get_logger
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.notifications.service import NotificationService
from app.modules.tenants.models import Tenant

logger = get_logger(__name__)
from app.modules.leads.schemas import (
    InquiryAnalytics,
    InquiryAnalyticsSummary,
    InquiryCreatePublic,
    InquiryFormCreate,
    InquiryFormResponse,
    InquiryFormUpdate,
    InquiryListResponse,
    InquiryProductBrief,
    InquiryResponse,
    InquiryUpdate,
)
from app.modules.leads.service import InquiryFormService, InquiryService


def _build_inquiry_response(inquiry) -> InquiryResponse:
    """Build InquiryResponse with enriched form_slug and product fields."""
    updates: dict = {}
    if inquiry.form:
        updates["form_slug"] = inquiry.form.slug
    if inquiry.product:
        p = inquiry.product
        updates["product"] = InquiryProductBrief(
            id=p.id,
            slug=p.slug,
            sku=p.sku,
            name=p.title,
        )
    r = InquiryResponse.model_validate(inquiry)
    return r.model_copy(update=updates) if updates else r

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

    response = _build_inquiry_response(inquiry)

    # Send notifications if enabled for this tenant (fire-and-forget)
    await _send_inquiry_notification(db, tenant_id, inquiry)

    return response


@router.post(
    "/public/inquiries/upload",
    response_model=InquiryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit inquiry (multipart/form-data)",
    description="Submit an inquiry from FormData. Same fields as POST /public/inquiries. Optional file attachments (future). Rate limited.",
    tags=["Public - Leads"],
)
async def create_inquiry_public_multipart(
    request: Request,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
    form_slug: str = Form(..., description="quick | mvp-brief"),
    name: str = Form(..., min_length=1, max_length=255),
    email: str = Form(None),
    phone: str = Form(None),
    company: str = Form(None),
    message: str = Form(None),
    telegram: str = Form(None),
    consent: str = Form(None),
    service_id: str | None = Form(None),
    analytics: str | None = Form(None, description="JSON: utm_source, source_url, etc."),
    idea: str | None = Form(None),
    market: str | None = Form(None),
    audience: str | None = Form(None),
    audienceSize: str | None = Form(None),
    aiRequired: str | None = Form(None),
    appTypes: list[str] | None = Form(None),
    integrations: str | None = Form(None),
    budget: str | None = Form(None),
    urgency: str | None = Form(None),
    source: str | None = Form(None),
    files: list[UploadFile] = File(default=[]),
) -> InquiryResponse:
    """Submit a public inquiry via multipart/form-data (for forms with file upload)."""
    analytics_obj = None
    if analytics:
        try:
            analytics_obj = json.loads(analytics)
        except json.JSONDecodeError:
            pass

    service_id_uuid = None
    if service_id:
        try:
            service_id_uuid = UUID(service_id)
        except ValueError:
            pass

    consent_bool = None
    if consent is not None:
        consent_bool = consent.strip().lower() in ("1", "true", "yes")

    data = InquiryCreatePublic(
        form_slug=form_slug,
        name=name,
        email=email or None,
        phone=phone or None,
        company=company or None,
        message=message or None,
        telegram=telegram or None,
        consent=consent_bool,
        service_id=service_id_uuid,
        analytics=InquiryAnalytics(**analytics_obj) if analytics_obj else None,
        idea=idea or None,
        market=market or None,
        audience=audience or None,
        audienceSize=audienceSize or None,
        aiRequired=aiRequired or None,
        appTypes=appTypes or None,
        integrations=integrations or None,
        budget=budget or None,
        urgency=urgency or None,
        source=source or None,
    )

    ip_address = None
    if request.client:
        ip_address = request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()

    service = InquiryService(db)
    inquiry = await service.create_from_public(tenant_id, data, ip_address)

    response = _build_inquiry_response(inquiry)

    await _send_inquiry_notification(db, tenant_id, inquiry)

    # TODO: handle files (upload to S3, add URLs to custom_fields.attachments)
    for f in files:
        await f.close()

    return response


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
        notification_service = NotificationService(db=db)
        
        # Build source info
        source_parts = []
        if inquiry.utm_source:
            source_parts.append(f"utm_source={inquiry.utm_source}")
        if inquiry.source_url:
            source_parts.append(inquiry.source_url)
        source = ", ".join(source_parts) if source_parts else None
        
        results = await notification_service.notify_inquiry(
            notification_email=settings.inquiry_email,
            telegram_chat_id=settings.telegram_chat_id,
            inquiry_name=inquiry.name,
            inquiry_email=inquiry.email,
            inquiry_phone=inquiry.phone,
            inquiry_message=inquiry.message,
            inquiry_source=source,
            tenant_id=tenant_id,
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
    form_slug: str | None = Query(default=None, alias="formSlug", description="Filter by form slug: quick, mvp-brief"),
    product_id: UUID | None = Query(default=None, alias="productId", description="Filter by product UUID"),
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
        form_slug=form_slug,
        product_id=product_id,
        assigned_to=assigned_to,
        utm_source=utm_source,
        search=search,
    )

    return InquiryListResponse(
        items=[_build_inquiry_response(i) for i in inquiries],
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
    return _build_inquiry_response(inquiry)


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
    return _build_inquiry_response(inquiry)


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

