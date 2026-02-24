"""Service routes for company module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Filtering, Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.middleware.feature_check import require_services, require_services_public
from app.modules.company.mappers import (
    map_service_to_public_response,
    map_services_to_public_response,
)
from app.modules.company.schemas import (
    ContentBlockForServiceResponse,
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
from app.modules.company.services import ServiceService
from app.modules.content.schemas import (
    ContentBlockCreate,
    ContentBlockReorderRequest,
    ContentBlockResponse,
    ContentBlockUpdate,
)
from app.modules.content.services import CaseService, ContentBlockService, ReviewService

router = APIRouter()


# ============================================================================
# Public Routes - Services
# ============================================================================


@router.get(
    "/public/services",
    response_model=list[ServicePublicResponse],
    summary="List published services",
    tags=["Public - Company"],
    dependencies=[require_services_public],
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
    dependencies=[require_services_public],
)
async def get_service_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> ServicePublicResponse:
    """Get a published service by slug with related cases, reviews, and content blocks."""
    service = ServiceService(db)
    svc = await service.get_by_slug(slug, locale.locale, tenant_id)
    
    # Get published cases linked to this service
    case_service = CaseService(db)
    cases = await case_service.list_published_by_service(svc.id, tenant_id, locale.locale)
    
    # Get approved reviews from cases linked to this service
    reviews = []
    if cases:
        review_service = ReviewService(db)
        case_ids = [c.id for c in cases]
        reviews = await review_service.list_approved_by_case_ids(case_ids, tenant_id)
    
    # Load content blocks for this service and locale
    content_block_service = ContentBlockService(db)
    content_blocks = await content_block_service.list_blocks("service", svc.id, tenant_id, locale.locale)
    
    return map_service_to_public_response(
        svc,
        locale.locale,
        cases=cases,
        reviews=reviews,
        content_blocks=content_blocks,
    )


# ============================================================================
# Admin Routes - Services
# ============================================================================


async def _service_response_with_blocks(
    svc, db: AsyncSession, tenant_id: UUID
) -> ServiceResponse:
    """Build ServiceResponse with content_blocks loaded (admin single-service responses)."""
    block_service = ContentBlockService(db)
    blocks = await block_service.list_blocks("service", svc.id, tenant_id, None)
    response = ServiceResponse.model_validate(svc)
    return response.model_copy(
        update={
            "content_blocks": [ContentBlockForServiceResponse.model_validate(b) for b in blocks]
        }
    )


@router.get(
    "/admin/services",
    response_model=ServiceListResponse,
    summary="List services (admin)",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:read"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:create"))],
)
async def create_service(
    data: ServiceCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Create a new service."""
    service = ServiceService(db)
    created = await service.create(tenant_id, data)
    return await _service_response_with_blocks(created, db, tenant_id)


@router.get(
    "/admin/services/{service_id}",
    response_model=ServiceResponse,
    summary="Get service",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:read"))],
)
async def get_service_admin(
    service_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Get service by ID."""
    service = ServiceService(db)
    svc = await service.get_by_id(service_id, tenant_id)
    return await _service_response_with_blocks(svc, db, tenant_id)


@router.patch(
    "/admin/services/{service_id}",
    response_model=ServiceResponse,
    summary="Update service",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    return await _service_response_with_blocks(updated, db, tenant_id)


@router.delete(
    "/admin/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:delete"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    
    svc = await service.update_image_url(service_id, tenant_id, new_url)
    
    return await _service_response_with_blocks(svc, db, tenant_id)


@router.delete(
    "/admin/services/{service_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service image",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
        await service.update_image_url(service_id, tenant_id, None)


# ============================================================================
# Admin Routes - Service Prices
# ============================================================================


@router.post(
    "/admin/services/{service_id}/prices",
    response_model=ServicePriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add price to service",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
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


# ============================================================================
# Admin Routes - Service Content Blocks
# ============================================================================


@router.get(
    "/admin/services/{service_id}/content-blocks",
    response_model=list[ContentBlockResponse],
    summary="List service content blocks",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:read"))],
)
async def list_service_content_blocks(
    service_id: UUID,
    locale: str | None = Query(default=None, description="Filter by locale"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ContentBlockResponse]:
    """List content blocks for a service, optionally filtered by locale."""
    # Verify service exists
    service_service = ServiceService(db)
    await service_service.get_by_id(service_id, tenant_id)
    
    service = ContentBlockService(db)
    blocks = await service.list_blocks("service", service_id, tenant_id, locale)
    return [ContentBlockResponse.model_validate(b) for b in blocks]


@router.post(
    "/admin/services/{service_id}/content-blocks",
    response_model=ContentBlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add service content block",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
)
async def add_service_content_block(
    service_id: UUID,
    data: ContentBlockCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContentBlockResponse:
    """Add a content block to a service (text, image, video, gallery, link)."""
    # Verify service exists
    service_service = ServiceService(db)
    await service_service.get_by_id(service_id, tenant_id)
    
    service = ContentBlockService(db)
    block = await service.add_block("service", service_id, tenant_id, data)
    return ContentBlockResponse.model_validate(block)


@router.patch(
    "/admin/services/{service_id}/content-blocks/{block_id}",
    response_model=ContentBlockResponse,
    summary="Update service content block",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
)
async def update_service_content_block(
    service_id: UUID,
    block_id: UUID,
    data: ContentBlockUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContentBlockResponse:
    """Update a service content block."""
    service = ContentBlockService(db)
    block = await service.update_block(block_id, "service", service_id, tenant_id, data)
    return ContentBlockResponse.model_validate(block)


@router.delete(
    "/admin/services/{service_id}/content-blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service content block",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
)
async def delete_service_content_block(
    service_id: UUID,
    block_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a content block from a service."""
    service = ContentBlockService(db)
    await service.delete_block(block_id, "service", service_id, tenant_id)


@router.post(
    "/admin/services/{service_id}/content-blocks/reorder",
    response_model=list[ContentBlockResponse],
    summary="Reorder service content blocks",
    tags=["Admin - Company"],
    dependencies=[require_services, Depends(PermissionChecker("services:update"))],
)
async def reorder_service_content_blocks(
    service_id: UUID,
    data: ContentBlockReorderRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ContentBlockResponse]:
    """Reorder content blocks for a service in a specific locale."""
    service = ContentBlockService(db)
    blocks = await service.reorder_blocks("service", service_id, tenant_id, data.locale, data.block_ids)
    return [ContentBlockResponse.model_validate(b) for b in blocks]
