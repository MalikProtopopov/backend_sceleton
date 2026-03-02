"""Case routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Locale, Pagination, PublicTenantId
from app.modules.media.upload_service import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.middleware.feature_check import require_cases, require_cases_public
from app.modules.content.mappers import (
    map_case_to_public_response,
    map_cases_to_public_response,
)
from app.modules.content.schemas import (
    CaseContactCreate,
    CaseContactResponse,
    CaseContactUpdate,
    CaseCreate,
    CaseListResponse,
    CaseLocaleCreate,
    CaseLocaleResponse,
    CaseLocaleUpdate,
    CasePublicListResponse,
    CasePublicResponse,
    CaseResponse,
    CaseUpdate,
    ContentBlockCreate,
    ContentBlockReorderRequest,
    ContentBlockResponse,
    ContentBlockUpdate,
)
from app.modules.content.services import CaseService, ReviewService
from app.modules.content_blocks.service import ContentBlockService

router = APIRouter()


# ============================================================================
# Public Routes - Cases
# ============================================================================


@router.get(
    "/public/cases",
    response_model=CasePublicListResponse,
    summary="List published cases",
    tags=["Public - Content"],
    dependencies=[require_cases_public],
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
    dependencies=[require_cases_public],
)
async def get_case_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> CasePublicResponse:
    """Get a published case by slug with approved reviews and content blocks."""
    service = CaseService(db)
    case = await service.get_by_slug(slug, locale.locale, tenant_id)
    
    review_service = ReviewService(db)
    reviews, _ = await review_service.list_approved(
        tenant_id=tenant_id,
        page=1,
        page_size=100,
        case_id=case.id,
    )
    
    # Load content blocks for this case and locale
    content_block_service = ContentBlockService(db)
    content_blocks = await content_block_service.list_blocks("case", case.id, tenant_id, locale.locale)
    
    return map_case_to_public_response(
        case,
        locale.locale,
        include_full_content=True,
        reviews=reviews,
        content_blocks=content_blocks,
    )


# ============================================================================
# Admin Routes - Cases
# ============================================================================


async def _case_response_with_blocks(
    case, db: AsyncSession, tenant_id: UUID
) -> CaseResponse:
    """Build CaseResponse with content_blocks loaded (admin single-case responses)."""
    block_service = ContentBlockService(db)
    blocks = await block_service.list_blocks("case", case.id, tenant_id, None)
    response = CaseResponse.model_validate(case)
    return response.model_copy(
        update={"content_blocks": [ContentBlockResponse.model_validate(b) for b in blocks]}
    )


@router.get(
    "/admin/cases",
    response_model=CaseListResponse,
    summary="List cases (admin)",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:read"))],
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
    dependencies=[require_cases, Depends(PermissionChecker("cases:create"))],
)
async def create_case(
    data: CaseCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Create a new case."""
    service = CaseService(db)
    case = await service.create(tenant_id, data)
    return await _case_response_with_blocks(case, db, tenant_id)


@router.get(
    "/admin/cases/{case_id}",
    response_model=CaseResponse,
    summary="Get case",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:read"))],
)
async def get_case_admin(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Get case by ID."""
    service = CaseService(db)
    case = await service.get_by_id(case_id, tenant_id)
    return await _case_response_with_blocks(case, db, tenant_id)


@router.patch(
    "/admin/cases/{case_id}",
    response_model=CaseResponse,
    summary="Update case",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
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
    return await _case_response_with_blocks(case, db, tenant_id)


@router.post(
    "/admin/cases/{case_id}/publish",
    response_model=CaseResponse,
    summary="Publish case",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:publish"))],
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
    return await _case_response_with_blocks(case, db, tenant_id)


@router.post(
    "/admin/cases/{case_id}/unpublish",
    response_model=CaseResponse,
    summary="Unpublish case",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:publish"))],
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
    return await _case_response_with_blocks(case, db, tenant_id)


@router.delete(
    "/admin/cases/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:delete"))],
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
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
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
    
    case = await service.update_cover_image_url(case_id, tenant_id, new_url)
    
    return await _case_response_with_blocks(case, db, tenant_id)


@router.delete(
    "/admin/cases/{case_id}/cover-image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case cover image",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
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
        await service.update_cover_image_url(case_id, tenant_id, None)


# ============================================================================
# Admin Routes - Case Locales
# ============================================================================


@router.post(
    "/admin/cases/{case_id}/locales",
    response_model=CaseLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to case",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
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
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
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
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
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


# ============================================================================
# Admin Routes - Case Contacts
# ============================================================================


@router.post(
    "/admin/cases/{case_id}/contacts",
    response_model=CaseContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add case contact",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
)
async def add_case_contact(
    case_id: UUID,
    data: CaseContactCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseContactResponse:
    """Add a contact to a case (website, social media, email, phone, etc.)."""
    service = CaseService(db)
    contact = await service.add_contact(case_id, tenant_id, data)
    return CaseContactResponse.model_validate(contact)


@router.patch(
    "/admin/cases/{case_id}/contacts/{contact_id}",
    response_model=CaseContactResponse,
    summary="Update case contact",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
)
async def update_case_contact(
    case_id: UUID,
    contact_id: UUID,
    data: CaseContactUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseContactResponse:
    """Update a case contact."""
    service = CaseService(db)
    contact = await service.update_contact(contact_id, case_id, tenant_id, data)
    return CaseContactResponse.model_validate(contact)


@router.delete(
    "/admin/cases/{case_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case contact",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
)
async def delete_case_contact(
    case_id: UUID,
    contact_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a contact from a case."""
    service = CaseService(db)
    await service.delete_contact(contact_id, case_id, tenant_id)


# ============================================================================
# Admin Routes - Case Content Blocks
# ============================================================================


@router.get(
    "/admin/cases/{case_id}/content-blocks",
    response_model=list[ContentBlockResponse],
    summary="List case content blocks",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:read"))],
)
async def list_case_content_blocks(
    case_id: UUID,
    locale: str | None = Query(default=None, description="Filter by locale"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ContentBlockResponse]:
    """List content blocks for a case, optionally filtered by locale."""
    # Verify case exists
    case_service = CaseService(db)
    await case_service.get_by_id(case_id, tenant_id)
    
    service = ContentBlockService(db)
    blocks = await service.list_blocks("case", case_id, tenant_id, locale)
    return [ContentBlockResponse.model_validate(b) for b in blocks]


@router.post(
    "/admin/cases/{case_id}/content-blocks",
    response_model=ContentBlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add case content block",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
)
async def add_case_content_block(
    case_id: UUID,
    data: ContentBlockCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContentBlockResponse:
    """Add a content block to a case (text, image, video, gallery, link, result)."""
    # Verify case exists
    case_service = CaseService(db)
    await case_service.get_by_id(case_id, tenant_id)
    
    service = ContentBlockService(db)
    block = await service.add_block("case", case_id, tenant_id, data)
    return ContentBlockResponse.model_validate(block)


@router.patch(
    "/admin/cases/{case_id}/content-blocks/{block_id}",
    response_model=ContentBlockResponse,
    summary="Update case content block",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
)
async def update_case_content_block(
    case_id: UUID,
    block_id: UUID,
    data: ContentBlockUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContentBlockResponse:
    """Update a case content block."""
    service = ContentBlockService(db)
    block = await service.update_block(block_id, "case", case_id, tenant_id, data)
    return ContentBlockResponse.model_validate(block)


@router.delete(
    "/admin/cases/{case_id}/content-blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case content block",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
)
async def delete_case_content_block(
    case_id: UUID,
    block_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a content block from a case."""
    service = ContentBlockService(db)
    await service.delete_block(block_id, "case", case_id, tenant_id)


@router.post(
    "/admin/cases/{case_id}/content-blocks/reorder",
    response_model=list[ContentBlockResponse],
    summary="Reorder case content blocks",
    tags=["Admin - Content"],
    dependencies=[require_cases, Depends(PermissionChecker("cases:update"))],
)
async def reorder_case_content_blocks(
    case_id: UUID,
    data: ContentBlockReorderRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ContentBlockResponse]:
    """Reorder content blocks for a case in a specific locale."""
    service = ContentBlockService(db)
    blocks = await service.reorder_blocks("case", case_id, tenant_id, data.locale, data.block_ids)
    return [ContentBlockResponse.model_validate(b) for b in blocks]
