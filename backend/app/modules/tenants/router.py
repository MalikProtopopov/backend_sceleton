"""API routes for tenants and feature flags."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
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
    FeatureFlagResponse,
    FeatureFlagsListResponse,
    FeatureFlagUpdate,
    TenantCreate,
    TenantListResponse,
    TenantPublicResponse,
    TenantResponse,
    TenantSettingsResponse,
    TenantSettingsUpdate,
    TenantUpdate,
)
from app.modules.tenants.service import FeatureFlagService, TenantService

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
    description="Get public tenant information (name, logo, branding) for frontend.",
    tags=["Public"],
)
async def get_tenant_public(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TenantPublicResponse:
    """Get public tenant information.
    
    Returns only non-sensitive data: name, slug, logo_url, primary_color.
    Does not require authentication.
    """
    service = TenantService(db)
    tenant = await service.get_by_id(tenant_id)
    
    return TenantPublicResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
    )


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
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
) -> TenantListResponse:
    """List all tenants with pagination.
    
    Only platform owners and superusers can access this endpoint.
    """
    service = TenantService(db)
    tenants, total = await service.list_tenants(
        page=pagination.page,
        page_size=pagination.page_size,
        is_active=is_active,
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
    service = TenantService(db)
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
    
    service = TenantService(db)
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
    service = TenantService(db)
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
    settings = await service.update_settings(tenant_id, data)
    return TenantSettingsResponse.model_validate(settings)


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
    
    service = FeatureFlagService(db)
    flag = await service.update_flag(effective_tenant_id, feature_name, data)
    return FeatureFlagResponse.model_validate(flag)

