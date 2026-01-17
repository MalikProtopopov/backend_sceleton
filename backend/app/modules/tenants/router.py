"""API routes for tenants and feature flags."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination
from app.core.image_upload import image_upload_service
from app.core.security import get_current_tenant_id, require_platform_owner
from app.modules.auth.models import AdminUser
from app.modules.tenants.models import AVAILABLE_FEATURES
from app.modules.tenants.schemas import (
    FeatureFlagResponse,
    FeatureFlagsListResponse,
    FeatureFlagUpdate,
    TenantCreate,
    TenantListResponse,
    TenantResponse,
    TenantSettingsResponse,
    TenantSettingsUpdate,
    TenantUpdate,
)
from app.modules.tenants.service import FeatureFlagService, TenantService

router = APIRouter()


# ============================================================================
# Tenant Routes
# ============================================================================


@router.get(
    "/tenants",
    response_model=TenantListResponse,
    summary="List all tenants",
    description="Get paginated list of all tenants. Admin only.",
)
async def list_tenants(
    pagination: Pagination,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
) -> TenantListResponse:
    """List all tenants with pagination."""
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
    description="Create a new tenant with default settings and feature flags.",
)
async def create_tenant(
    data: TenantCreate,
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Create a new tenant."""
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
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Get tenant details by ID."""
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
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Update tenant with optimistic locking."""
    service = TenantService(db)
    tenant = await service.update(tenant_id, data)
    return TenantResponse.model_validate(tenant)


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tenant",
    description="Soft delete a tenant. Data is preserved but marked as deleted.",
)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a tenant."""
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
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Upload or replace tenant logo.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
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
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete tenant logo."""
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
    db: AsyncSession = Depends(get_db),
) -> TenantSettingsResponse:
    """Update tenant settings."""
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
    description="Get all feature flags for the current tenant. Requires platform_owner role.",
)
async def list_feature_flags(
    user: AdminUser = Depends(require_platform_owner),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FeatureFlagsListResponse:
    """List all feature flags for a tenant.
    
    Only platform_owner or superuser can access this endpoint.
    """
    service = FeatureFlagService(db)
    flags = await service.get_flags(tenant_id)

    return FeatureFlagsListResponse(
        items=[FeatureFlagResponse.model_validate(f) for f in flags],
        available_features=AVAILABLE_FEATURES,
    )


@router.patch(
    "/feature-flags/{feature_name}",
    response_model=FeatureFlagResponse,
    summary="Update feature flag",
    description="Enable or disable a feature flag. Requires platform_owner role.",
)
async def update_feature_flag(
    feature_name: str,
    data: FeatureFlagUpdate,
    user: AdminUser = Depends(require_platform_owner),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FeatureFlagResponse:
    """Update a feature flag.
    
    Only platform_owner or superuser can enable/disable features.
    """
    service = FeatureFlagService(db)
    flag = await service.update_flag(tenant_id, feature_name, data)
    return FeatureFlagResponse.model_validate(flag)

