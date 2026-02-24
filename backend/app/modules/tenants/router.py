"""API routes for tenants and feature flags."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination
from app.core.exceptions import PermissionDeniedError
from app.core.image_upload import image_upload_service
from app.core.security import (
    get_current_active_user,
    get_current_tenant_id,
    require_platform_owner,
)
from app.modules.auth.models import AdminUser
from app.modules.tenants.models import AVAILABLE_FEATURES
from app.modules.tenants.schemas import (
    DNSVerifyResponse,
    EmailLogListResponse,
    EmailLogResponse,
    EmailTestRequest,
    EmailTestResponse,
    FeatureFlagResponse,
    FeatureFlagsListResponse,
    FeatureFlagUpdate,
    TenantAnalyticsPublic,
    TenantByDomainResponse,
    TenantCreate,
    TenantDomainCreate,
    TenantDomainListResponse,
    TenantDomainResponse,
    TenantDomainSSLStatusResponse,
    TenantDomainUpdate,
    TenantListResponse,
    TenantPublicResponse,
    TenantResponse,
    TenantSettingsResponse,
    TenantSettingsUpdate,
    TenantUpdate,
)
from app.modules.tenants.service import FeatureFlagService, TenantDomainService, TenantService

router = APIRouter()


# ============================================================================
# Helper Functions
# ============================================================================


def check_tenant_access(
    user: AdminUser,
    tenant_id: UUID,
    current_tenant_id: UUID,
) -> None:
    """Check if user can access the specified tenant.
    
    Raises PermissionDeniedError if user cannot access the tenant.
    
    - Superusers can access any tenant
    - Platform owners can access any tenant
    - Regular admins can only access their own tenant
    """
    if user.is_superuser:
        return
    if user.role and user.role.name == "platform_owner":
        return
    if tenant_id != current_tenant_id:
        raise PermissionDeniedError(
            required_permission="platform:read",
            detail="You can only access your own tenant",
        )


# ============================================================================
# Public Routes
# ============================================================================


@router.get(
    "/public/tenants/{tenant_id}",
    response_model=TenantPublicResponse,
    summary="Get tenant info (public)",
    description="Get public tenant information (name, logo, branding, site URL) for frontend.",
    tags=["Public"],
)
async def get_tenant_public(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TenantPublicResponse:
    """Get public tenant information.
    
    Returns only non-sensitive data: name, slug, logo_url, primary_color, site_url.
    Does not require authentication.
    """
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    
    # Extract site_url from tenant settings (if available)
    site_url = None
    if tenant.settings and tenant.settings.site_url:
        site_url = tenant.settings.site_url
    
    return TenantPublicResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        site_url=site_url,
    )


@router.get(
    "/public/tenants/by-domain/{domain}",
    response_model=TenantByDomainResponse,
    summary="Resolve tenant by domain (public)",
    description=(
        "Resolve a custom admin-panel domain (e.g. admin.client.com) to tenant info. "
        "Used by the admin SPA at startup to determine which tenant to load."
    ),
    tags=["Public"],
)
async def resolve_tenant_by_domain(
    domain: str,
    db: AsyncSession = Depends(get_db),
) -> TenantByDomainResponse:
    """Resolve hostname → tenant.

    Returns tenant_id, slug, name, logo, color, site_url.
    Result is cached in Redis for 5 min.
    """
    service = TenantDomainService(db)
    data = await service.resolve(domain)
    if data is None:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("TenantDomain", domain)
    return TenantByDomainResponse(**data)


@router.get(
    "/public/tenants/{tenant_id}/analytics",
    response_model=TenantAnalyticsPublic,
    summary="Get analytics scripts (public)",
    description="Get Google Analytics and Yandex.Metrika IDs/codes for tenant. Use in <head> to inject tracking scripts.",
    tags=["Public"],
)
async def get_tenant_analytics_public(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TenantAnalyticsPublic:
    """Get analytics configuration for frontend.
    
    Returns ga_tracking_id and ym_counter_id from tenant settings.
    ym_counter_id may be either a counter ID (e.g. 92699637) or full Yandex.Metrika embed HTML.
    """
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    settings = tenant.settings
    if not settings:
        return TenantAnalyticsPublic()
    return TenantAnalyticsPublic(
        ga_tracking_id=settings.ga_tracking_id or None,
        ym_counter_id=settings.ym_counter_id or None,
        google_verification_meta=settings.google_verification_meta or None,
    )


@router.get(
    "/public/tenants/{tenant_id}/verification/{filename}",
    response_class=HTMLResponse,
    summary="Get webmaster verification file",
    description=(
        "Returns Yandex.Webmaster or Google Search Console verification file "
        "for site ownership verification. The file content is generated "
        "dynamically based on the verification code stored in tenant settings."
    ),
    tags=["Public"],
)
async def get_verification_file(
    tenant_id: UUID,
    filename: str,
    db: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    """Get verification file for Yandex.Webmaster or Google Search Console.

    Supports:
    - Yandex: yandex_*.html
    - Google: google*.html
    """
    from app.core.exceptions import NotFoundError

    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)

    if not tenant.settings:
        raise NotFoundError("Verification file", filename)

    # Yandex verification
    if filename.startswith("yandex_") and filename.endswith(".html"):
        code = tenant.settings.yandex_verification_code
        if code and filename == f"{code}.html":
            verification_value = code.removeprefix("yandex_")
            content = (
                "<html>\n"
                "<head>\n"
                '    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n'
                "</head>\n"
                f"<body>Verification: {verification_value}</body>\n"
                "</html>"
            )
            return HTMLResponse(content=content)

    # Google verification
    if filename.startswith("google") and filename.endswith(".html"):
        code = tenant.settings.google_verification_code
        if code and filename == f"{code}.html":
            content = f"google-site-verification: {filename}"
            return HTMLResponse(content=content)

    raise NotFoundError("Verification file", filename)


# ============================================================================
# Tenant Routes (Admin)
# ============================================================================


@router.get(
    "/tenants",
    response_model=TenantListResponse,
    summary="List all tenants",
    description="Get paginated list of all tenants. Platform owner only.",
)
async def list_tenants(
    pagination: Pagination,
    is_active: bool | None = None,
    search: str | None = Query(default=None, description="Search tenants by name"),
    sort_by: str = Query(default="created_at", description="Sort by: name, created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"),
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantListResponse:
    """List all tenants with pagination.
    
    Only platform owners and superusers can access this endpoint.
    Supports search by name, filtering by is_active, and sorting.
    """
    service = TenantService(db)
    tenants, total = await service.list_tenants(
        page=pagination.page,
        page_size=pagination.page_size,
        is_active=is_active,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return TenantListResponse(
        items=[TenantResponse.model_validate(t) for t in tenants],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/tenants",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant",
    description="Create a new tenant with default settings and feature flags. Platform owner only.",
)
async def create_tenant(
    data: TenantCreate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Create a new tenant.
    
    Only platform owners and superusers can create new tenants.
    """
    service = TenantService(db, actor_id=user.id)
    tenant = await service.create(data)
    return TenantResponse.model_validate(tenant)


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant by ID",
)
async def get_tenant(
    tenant_id: UUID,
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Get tenant details by ID.
    
    Superusers and platform owners can access any tenant.
    Regular admins can only access their own tenant.
    """
    check_tenant_access(user, tenant_id, current_tenant_id)
    
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    return TenantResponse.model_validate(tenant)


@router.patch(
    "/tenants/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant",
    description="Update tenant. Requires version field for optimistic locking.",
)
async def update_tenant(
    tenant_id: UUID,
    data: TenantUpdate,
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Update tenant with optimistic locking.
    
    Superusers and platform owners can update any tenant.
    Regular admins can only update their own tenant.
    """
    check_tenant_access(user, tenant_id, current_tenant_id)
    
    service = TenantService(db, actor_id=user.id)
    tenant = await service.update(tenant_id, data)
    return TenantResponse.model_validate(tenant)


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant",
    description="Soft delete a tenant. Data is preserved but marked as deleted. Platform owner only.",
)
async def delete_tenant(
    tenant_id: UUID,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a tenant.
    
    Only platform owners and superusers can delete tenants.
    """
    service = TenantService(db, actor_id=user.id)
    await service.soft_delete(tenant_id)


@router.post(
    "/tenants/{tenant_id}/logo",
    response_model=TenantResponse,
    summary="Upload tenant logo",
    description="Upload or replace the tenant's logo image.",
)
async def upload_tenant_logo(
    tenant_id: UUID,
    file: UploadFile = File(...),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Upload or replace tenant logo.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    
    Superusers and platform owners can upload for any tenant.
    Regular admins can only upload for their own tenant.
    """
    check_tenant_access(user, tenant_id, current_tenant_id)
    
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    
    # Upload new logo
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="tenants",
        entity_id=tenant_id,
        old_image_url=tenant.logo_url,
    )
    
    # Update tenant
    tenant.logo_url = new_url
    await db.commit()
    await db.refresh(tenant)
    
    return TenantResponse.model_validate(tenant)


@router.delete(
    "/tenants/{tenant_id}/logo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant logo",
    description="Delete the tenant's logo image.",
)
async def delete_tenant_logo(
    tenant_id: UUID,
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete tenant logo.
    
    Superusers and platform owners can delete logo for any tenant.
    Regular admins can only delete logo for their own tenant.
    """
    check_tenant_access(user, tenant_id, current_tenant_id)
    
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    
    if tenant.logo_url:
        await image_upload_service.delete_image(tenant.logo_url)
        tenant.logo_url = None
        await db.commit()


# ============================================================================
# Tenant Domain Routes (platform owner)
# ============================================================================


@router.get(
    "/tenants/{tenant_id}/domains",
    response_model=TenantDomainListResponse,
    summary="List tenant domains",
    description="List all custom domains attached to a tenant. Platform owner only.",
)
async def list_tenant_domains(
    tenant_id: UUID,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantDomainListResponse:
    """List all domains for a tenant."""
    service = TenantDomainService(db)
    domains = await service.list_domains(tenant_id)
    return TenantDomainListResponse(
        items=[TenantDomainResponse.model_validate(d) for d in domains],
        total=len(domains),
    )


@router.post(
    "/tenants/{tenant_id}/domains",
    response_model=TenantDomainResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add domain to tenant",
    description="Attach a new custom admin-panel domain to a tenant. Platform owner only.",
)
async def add_tenant_domain(
    tenant_id: UUID,
    data: TenantDomainCreate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantDomainResponse:
    """Add a domain to a tenant."""
    service = TenantDomainService(db)
    td = await service.add_domain(tenant_id, data)
    return TenantDomainResponse.model_validate(td)


@router.patch(
    "/tenants/{tenant_id}/domains/{domain_id}",
    response_model=TenantDomainResponse,
    summary="Update tenant domain",
    description="Update domain attributes (is_primary, ssl_status). Platform owner only.",
)
async def update_tenant_domain(
    tenant_id: UUID,
    domain_id: UUID,
    data: TenantDomainUpdate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantDomainResponse:
    """Update a domain."""
    service = TenantDomainService(db)
    td = await service.update_domain(domain_id, data)
    return TenantDomainResponse.model_validate(td)


@router.delete(
    "/tenants/{tenant_id}/domains/{domain_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tenant domain",
    description="Remove a custom domain from a tenant. Platform owner only.",
)
async def remove_tenant_domain(
    tenant_id: UUID,
    domain_id: UUID,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a domain binding."""
    service = TenantDomainService(db)
    await service.remove_domain(domain_id)


@router.get(
    "/tenants/{tenant_id}/domains/{domain_id}/ssl-status",
    response_model=TenantDomainSSLStatusResponse,
    summary="Get domain SSL status",
    description=(
        "Check the current SSL provisioning status for a domain. "
        "Use for polling after adding a domain or triggering DNS verification. "
        "Platform owner only."
    ),
)
async def get_domain_ssl_status(
    tenant_id: UUID,
    domain_id: UUID,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantDomainSSLStatusResponse:
    """Return lightweight SSL status for polling."""
    service = TenantDomainService(db)
    td = await service.get_domain(domain_id)

    status_messages = {
        "pending": "Waiting for DNS configuration",
        "verifying": "DNS verified, obtaining SSL certificate...",
        "active": "SSL certificate is active",
        "error": "SSL provisioning failed — check DNS configuration",
    }

    return TenantDomainSSLStatusResponse(
        domain_id=td.id,
        domain=td.domain,
        ssl_status=td.ssl_status,
        dns_verified_at=td.dns_verified_at,
        ssl_provisioned_at=td.ssl_provisioned_at,
        message=status_messages.get(td.ssl_status),
    )


@router.post(
    "/tenants/{tenant_id}/domains/{domain_id}/verify",
    response_model=DNSVerifyResponse,
    summary="Verify domain DNS configuration",
    description=(
        "Check if the domain's DNS CNAME record is correctly configured. "
        "If DNS is valid, triggers SSL provisioning in the background. "
        "Platform owner only."
    ),
)
async def verify_domain_dns(
    tenant_id: UUID,
    domain_id: UUID,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> DNSVerifyResponse:
    """Verify DNS and optionally trigger provisioning."""
    from app.services.domain_provisioning import DomainProvisioningService
    from app.tasks.domain_tasks import provision_domain_task

    service = DomainProvisioningService(db)
    result = await service.verify_dns_only(domain_id)
    await db.commit()

    if result["ok"]:
        await provision_domain_task.kiq(str(domain_id))

    return DNSVerifyResponse(**result)


# ============================================================================
# Tenant Settings Routes
# ============================================================================


@router.put(
    "/tenants/{tenant_id}/settings",
    response_model=TenantSettingsResponse,
    summary="Update tenant settings",
)
async def update_tenant_settings(
    tenant_id: UUID,
    data: TenantSettingsUpdate,
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsResponse:
    """Update tenant settings.
    
    Superusers and platform owners can update settings for any tenant.
    Regular admins can only update settings for their own tenant.
    """
    check_tenant_access(user, tenant_id, current_tenant_id)
    
    service = TenantService(db)
    tenant_settings = await service.update_settings(tenant_id, data)
    return TenantSettingsResponse.model_validate(tenant_settings)


# ============================================================================
# Email Test & Logs Routes
# ============================================================================


@router.post(
    "/tenants/{tenant_id}/settings/email-test",
    response_model=EmailTestResponse,
    summary="Send test email",
    description="Send a test email using the tenant's email configuration to verify SMTP/provider setup.",
)
async def send_email_test(
    tenant_id: UUID,
    data: EmailTestRequest,
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailTestResponse:
    """Send a test email using tenant's email config.

    Sends a test message to the specified address to verify configuration.
    Requires settings:update permission.
    """
    check_tenant_access(user, tenant_id, current_tenant_id)

    from app.modules.notifications.service import EmailService

    email_service = EmailService(db=db)
    success, error = await email_service.send_test_email(
        to_email=data.to_email,
        tenant_id=tenant_id,
    )

    # Commit the email log entry
    await db.commit()

    # Determine the provider used
    config = await email_service._resolve_config(tenant_id)

    return EmailTestResponse(
        success=success,
        provider=config.provider,
        error=error,
    )


@router.get(
    "/tenants/{tenant_id}/email-logs",
    response_model=EmailLogListResponse,
    summary="List email logs",
    description="Get paginated list of email send attempts for a tenant. Useful for debugging invitation delivery.",
)
async def list_email_logs(
    tenant_id: UUID,
    pagination: Pagination,
    email_status: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status: sent, failed, console",
    ),
    email_type: str | None = Query(
        default=None,
        alias="type",
        description="Filter by type: welcome, password_reset, inquiry, test",
    ),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmailLogListResponse:
    """List email logs for a tenant with pagination and filters.

    Superusers and platform owners can view logs for any tenant.
    Regular admins can only view logs for their own tenant.
    """
    check_tenant_access(user, tenant_id, current_tenant_id)

    from app.modules.notifications.models import EmailLog

    base_query = select(EmailLog).where(EmailLog.tenant_id == tenant_id)

    if email_status:
        base_query = base_query.where(EmailLog.status == email_status)
    if email_type:
        base_query = base_query.where(EmailLog.email_type == email_type)

    # Count total
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Paginated results (newest first)
    stmt = (
        base_query
        .order_by(EmailLog.created_at.desc())
        .offset((pagination.page - 1) * pagination.page_size)
        .limit(pagination.page_size)
    )
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    return EmailLogListResponse(
        items=[EmailLogResponse.model_validate(log) for log in logs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ============================================================================
# Feature Flag Routes
# ============================================================================


@router.get(
    "/feature-flags",
    response_model=FeatureFlagsListResponse,
    summary="List feature flags",
    description="Get all feature flags for a tenant. Platform owner can specify tenant_id to manage any tenant's flags.",
)
async def list_feature_flags(
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant ID (platform owner only)"),
    user: AdminUser = Depends(require_platform_owner),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FeatureFlagsListResponse:
    """List all feature flags for a tenant.
    
    Platform owner or superuser can access this endpoint.
    If tenant_id query parameter is provided, returns flags for that tenant.
    Otherwise, returns flags for the current user's tenant.
    """
    # Determine which tenant to use
    effective_tenant_id = target_tenant_id if target_tenant_id else current_tenant_id
    
    # Verify tenant exists if explicitly specified
    if target_tenant_id:
        tenant_service = TenantService(db)
        await tenant_service.get_by_id(target_tenant_id)
    
    service = FeatureFlagService(db)
    flags = await service.get_flags(effective_tenant_id)

    return FeatureFlagsListResponse(
        items=[FeatureFlagResponse.model_validate(f) for f in flags],
        available_features=AVAILABLE_FEATURES,
    )


@router.patch(
    "/feature-flags/{feature_name}",
    response_model=FeatureFlagResponse,
    summary="Update feature flag",
    description="Enable or disable a feature flag. Platform owner can specify tenant_id to manage any tenant's flags.",
)
async def update_feature_flag(
    feature_name: str,
    data: FeatureFlagUpdate,
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant ID (platform owner only)"),
    user: AdminUser = Depends(require_platform_owner),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FeatureFlagResponse:
    """Update a feature flag.
    
    Platform owner or superuser can enable/disable features.
    If tenant_id query parameter is provided, updates flag for that tenant.
    Otherwise, updates flag for the current user's tenant.
    """
    # Determine which tenant to use
    effective_tenant_id = target_tenant_id if target_tenant_id else current_tenant_id
    
    # Verify tenant exists if explicitly specified
    if target_tenant_id:
        tenant_service = TenantService(db)
        await tenant_service.get_by_id(target_tenant_id)
    
    service = FeatureFlagService(db, actor_id=user.id)
    flag = await service.update_flag(effective_tenant_id, feature_name, data)
    return FeatureFlagResponse.model_validate(flag)

