"""Service routes for company module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Filtering, Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.company.mappers import (
    map_service_to_public_response,
    map_services_to_public_response,
)
from app.modules.company.schemas import (
    ServiceCreate,
    ServiceListResponse,
    ServiceLocaleCreate,
    ServiceLocaleResponse,
    ServiceLocaleUpdate,
    ServicePriceCreate,
    ServicePriceResponse,
    ServicePriceUpdate,
    ServicePublicResponse,
    ServiceResponse,
    ServiceTagCreate,
    ServiceTagResponse,
    ServiceUpdate,
)
from app.modules.company.service import ServiceService

router = APIRouter()


# ============================================================================
# Public Routes - Services
# ============================================================================


@router.get(
    "/public/services",
    response_model=list[ServicePublicResponse],
    summary="List published services",
    tags=["Public - Company"],
)
async def list_services_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> list[ServicePublicResponse]:
    """List all published services for public display."""
    service = ServiceService(db)
    services = await service.list_published(tenant_id, locale.locale)
    return map_services_to_public_response(services, locale.locale)


@router.get(
    "/public/services/{slug}",
    response_model=ServicePublicResponse,
    summary="Get service by slug",
    tags=["Public - Company"],
)
async def get_service_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> ServicePublicResponse:
    """Get a published service by slug."""
    service = ServiceService(db)
    svc = await service.get_by_slug(slug, locale.locale, tenant_id)
    return map_service_to_public_response(svc, locale.locale)


# ============================================================================
# Admin Routes - Services
# ============================================================================


@router.get(
    "/admin/services",
    response_model=ServiceListResponse,
    summary="List services (admin)",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def list_services_admin(
    pagination: Pagination,
    filtering: Filtering,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceListResponse:
    """List all services with pagination."""
    service = ServiceService(db)
    services, total = await service.list_services(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        is_published=filtering.is_published,
    )

    return ServiceListResponse(
        items=[ServiceResponse.model_validate(s) for s in services],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:create"))],
)
async def create_service(
    data: ServiceCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Create a new service."""
    service = ServiceService(db)
    created = await service.create(tenant_id, data)
    return ServiceResponse.model_validate(created)


@router.get(
    "/admin/services/{service_id}",
    response_model=ServiceResponse,
    summary="Get service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def get_service_admin(
    service_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Get service by ID."""
    service = ServiceService(db)
    svc = await service.get_by_id(service_id, tenant_id)
    return ServiceResponse.model_validate(svc)


@router.patch(
    "/admin/services/{service_id}",
    response_model=ServiceResponse,
    summary="Update service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service(
    service_id: UUID,
    data: ServiceUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Update a service."""
    service = ServiceService(db)
    await service.update(service_id, tenant_id, data)
    updated = await service.get_by_id(service_id, tenant_id)
    return ServiceResponse.model_validate(updated)


@router.delete(
    "/admin/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:delete"))],
)
async def delete_service(
    service_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a service."""
    service = ServiceService(db)
    await service.soft_delete(service_id, tenant_id)


@router.post(
    "/admin/services/{service_id}/image",
    response_model=ServiceResponse,
    summary="Upload service image",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def upload_service_image(
    service_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Upload or replace image for service."""
    service = ServiceService(db)
    svc = await service.get_by_id(service_id, tenant_id)
    
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="services",
        entity_id=service_id,
        old_image_url=svc.image_url,
    )
    
    svc.image_url = new_url
    await db.commit()
    svc = await service.get_by_id(service_id, tenant_id)
    
    return ServiceResponse.model_validate(svc)


@router.delete(
    "/admin/services/{service_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service image",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_image(
    service_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete image from service."""
    service = ServiceService(db)
    svc = await service.get_by_id(service_id, tenant_id)
    
    if svc.image_url:
        await image_upload_service.delete_image(svc.image_url)
        svc.image_url = None
        await db.commit()


# ============================================================================
# Admin Routes - Service Prices
# ============================================================================


@router.post(
    "/admin/services/{service_id}/prices",
    response_model=ServicePriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add price to service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_service_price(
    service_id: UUID,
    data: ServicePriceCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServicePriceResponse:
    """Add a price for a service in a specific locale and currency."""
    service = ServiceService(db)
    price = await service.create_price(service_id, tenant_id, data)
    return ServicePriceResponse.model_validate(price)


@router.patch(
    "/admin/services/{service_id}/prices/{price_id}",
    response_model=ServicePriceResponse,
    summary="Update service price",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service_price(
    service_id: UUID,
    price_id: UUID,
    data: ServicePriceUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServicePriceResponse:
    """Update a service price."""
    service = ServiceService(db)
    price = await service.update_price(price_id, service_id, tenant_id, data)
    return ServicePriceResponse.model_validate(price)


@router.delete(
    "/admin/services/{service_id}/prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service price",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_price(
    service_id: UUID,
    price_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a price from service."""
    service = ServiceService(db)
    await service.delete_price(price_id, service_id, tenant_id)


# ============================================================================
# Admin Routes - Service Tags
# ============================================================================


@router.post(
    "/admin/services/{service_id}/tags",
    response_model=ServiceTagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add tag to service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_service_tag(
    service_id: UUID,
    data: ServiceTagCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceTagResponse:
    """Add a tag to a service in a specific locale."""
    service = ServiceService(db)
    tag = await service.create_tag(service_id, tenant_id, data)
    return ServiceTagResponse.model_validate(tag)


@router.patch(
    "/admin/services/{service_id}/tags/{tag_id}",
    response_model=ServiceTagResponse,
    summary="Update service tag",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service_tag(
    service_id: UUID,
    tag_id: UUID,
    data: ServiceTagCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceTagResponse:
    """Update a service tag."""
    service = ServiceService(db)
    tag = await service.update_tag(tag_id, service_id, tenant_id, data)
    return ServiceTagResponse.model_validate(tag)


@router.delete(
    "/admin/services/{service_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service tag",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_tag(
    service_id: UUID,
    tag_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tag from service."""
    service = ServiceService(db)
    await service.delete_tag(tag_id, service_id, tenant_id)


# ============================================================================
# Admin Routes - Service Locales
# ============================================================================


@router.post(
    "/admin/services/{service_id}/locales",
    response_model=ServiceLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_service_locale(
    service_id: UUID,
    data: ServiceLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceLocaleResponse:
    """Add a new locale to a service."""
    service = ServiceService(db)
    locale = await service.create_locale(service_id, tenant_id, data)
    return ServiceLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/services/{service_id}/locales/{locale_id}",
    response_model=ServiceLocaleResponse,
    summary="Update service locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service_locale(
    service_id: UUID,
    locale_id: UUID,
    data: ServiceLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceLocaleResponse:
    """Update a service locale."""
    service = ServiceService(db)
    locale = await service.update_locale(locale_id, service_id, tenant_id, data)
    return ServiceLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/services/{service_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_locale(
    service_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from service (minimum 1 locale required)."""
    service = ServiceService(db)
    await service.delete_locale(locale_id, service_id, tenant_id)
