"""Case routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.content.mappers import (
    map_case_to_public_response,
    map_cases_to_public_response,
)
from app.modules.content.schemas import (
    CaseCreate,
    CaseListResponse,
    CaseLocaleCreate,
    CaseLocaleResponse,
    CaseLocaleUpdate,
    CasePublicListResponse,
    CasePublicResponse,
    CaseResponse,
    CaseUpdate,
)
from app.modules.content.service import CaseService, ReviewService

router = APIRouter()


# ============================================================================
# Public Routes - Cases
# ============================================================================


@router.get(
    "/public/cases",
    response_model=CasePublicListResponse,
    summary="List published cases",
    tags=["Public - Content"],
)
async def list_cases_public(
    locale: Locale,
    pagination: Pagination,
    tenant_id: PublicTenantId,
    featured: bool | None = Query(default=None, description="Filter by featured"),
    db: AsyncSession = Depends(get_db),
) -> CasePublicListResponse:
    """List published cases for public display."""
    service = CaseService(db)
    cases, total = await service.list_published(
        tenant_id=tenant_id,
        locale=locale.locale,
        page=pagination.page,
        page_size=pagination.page_size,
        is_featured=featured,
    )

    items = map_cases_to_public_response(cases, locale.locale, include_full_content=False)

    return CasePublicListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/public/cases/{slug}",
    response_model=CasePublicResponse,
    summary="Get case by slug",
    tags=["Public - Content"],
)
async def get_case_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> CasePublicResponse:
    """Get a published case by slug with approved reviews."""
    service = CaseService(db)
    case = await service.get_by_slug(slug, locale.locale, tenant_id)
    
    review_service = ReviewService(db)
    reviews, _ = await review_service.list_approved(
        tenant_id=tenant_id,
        page=1,
        page_size=100,
        case_id=case.id,
    )
    
    return map_case_to_public_response(
        case, locale.locale, include_full_content=True, reviews=reviews
    )


# ============================================================================
# Admin Routes - Cases
# ============================================================================


@router.get(
    "/admin/cases",
    response_model=CaseListResponse,
    summary="List cases (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:read"))],
)
async def list_cases_admin(
    pagination: Pagination,
    case_status: str | None = Query(default=None, alias="status"),
    featured: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Search in title and client name"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    """List all cases with filters."""
    service = CaseService(db)
    cases, total = await service.list_cases(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=case_status,
        is_featured=featured,
        search=search,
    )

    return CaseListResponse(
        items=[CaseResponse.model_validate(c) for c in cases],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/cases",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:create"))],
)
async def create_case(
    data: CaseCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Create a new case."""
    service = CaseService(db)
    case = await service.create(tenant_id, data)
    return CaseResponse.model_validate(case)


@router.get(
    "/admin/cases/{case_id}",
    response_model=CaseResponse,
    summary="Get case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:read"))],
)
async def get_case_admin(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Get case by ID."""
    service = CaseService(db)
    case = await service.get_by_id(case_id, tenant_id)
    return CaseResponse.model_validate(case)


@router.patch(
    "/admin/cases/{case_id}",
    response_model=CaseResponse,
    summary="Update case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def update_case(
    case_id: UUID,
    data: CaseUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Update a case."""
    service = CaseService(db)
    case = await service.update(case_id, tenant_id, data)
    return CaseResponse.model_validate(case)


@router.post(
    "/admin/cases/{case_id}/publish",
    response_model=CaseResponse,
    summary="Publish case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:publish"))],
)
async def publish_case(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Publish a case."""
    service = CaseService(db)
    await service.publish(case_id, tenant_id)
    case = await service.get_by_id(case_id, tenant_id)
    return CaseResponse.model_validate(case)


@router.post(
    "/admin/cases/{case_id}/unpublish",
    response_model=CaseResponse,
    summary="Unpublish case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:publish"))],
)
async def unpublish_case(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Unpublish a case (move to draft)."""
    service = CaseService(db)
    await service.unpublish(case_id, tenant_id)
    case = await service.get_by_id(case_id, tenant_id)
    return CaseResponse.model_validate(case)


@router.delete(
    "/admin/cases/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:delete"))],
)
async def delete_case(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a case."""
    service = CaseService(db)
    await service.soft_delete(case_id, tenant_id)


@router.post(
    "/admin/cases/{case_id}/cover-image",
    response_model=CaseResponse,
    summary="Upload case cover image",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def upload_case_cover_image(
    case_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Upload or replace cover image for case."""
    service = CaseService(db)
    case = await service.get_by_id(case_id, tenant_id)
    
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="cases",
        entity_id=case_id,
        old_image_url=case.cover_image_url,
    )
    
    case.cover_image_url = new_url
    await db.commit()
    case = await service.get_by_id(case_id, tenant_id)
    
    return CaseResponse.model_validate(case)


@router.delete(
    "/admin/cases/{case_id}/cover-image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case cover image",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def delete_case_cover_image(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete cover image from case."""
    service = CaseService(db)
    case = await service.get_by_id(case_id, tenant_id)
    
    if case.cover_image_url:
        await image_upload_service.delete_image(case.cover_image_url)
        case.cover_image_url = None
        await db.commit()


# ============================================================================
# Admin Routes - Case Locales
# ============================================================================


@router.post(
    "/admin/cases/{case_id}/locales",
    response_model=CaseLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def create_case_locale(
    case_id: UUID,
    data: CaseLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseLocaleResponse:
    """Add a new locale to a case."""
    service = CaseService(db)
    locale = await service.create_locale(case_id, tenant_id, data)
    return CaseLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/cases/{case_id}/locales/{locale_id}",
    response_model=CaseLocaleResponse,
    summary="Update case locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def update_case_locale(
    case_id: UUID,
    locale_id: UUID,
    data: CaseLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseLocaleResponse:
    """Update a case locale."""
    service = CaseService(db)
    locale = await service.update_locale(locale_id, case_id, tenant_id, data)
    return CaseLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/cases/{case_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def delete_case_locale(
    case_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from case (minimum 1 locale required)."""
    service = CaseService(db)
    await service.delete_locale(locale_id, case_id, tenant_id)
