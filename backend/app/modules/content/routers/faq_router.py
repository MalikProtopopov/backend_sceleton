"""FAQ routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Filtering, Locale, Pagination, PublicTenantId
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.content.mappers import map_faqs_to_public_response
from app.modules.content.schemas import (
    FAQCreate,
    FAQListResponse,
    FAQLocaleCreate,
    FAQLocaleResponse,
    FAQLocaleUpdate,
    FAQPublicResponse,
    FAQResponse,
    FAQUpdate,
)
from app.modules.content.service import FAQService

router = APIRouter()


# ============================================================================
# Public Routes - FAQ
# ============================================================================


@router.get(
    "/public/faq",
    response_model=list[FAQPublicResponse],
    summary="List FAQ",
    tags=["Public - Content"],
)
async def list_faq_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    category: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[FAQPublicResponse]:
    """List published FAQ items."""
    service = FAQService(db)
    faqs = await service.list_published(tenant_id, locale.locale, category)
    return map_faqs_to_public_response(faqs, locale.locale)


# ============================================================================
# Admin Routes - FAQ
# ============================================================================


@router.get(
    "/admin/faq",
    response_model=FAQListResponse,
    summary="List FAQ (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:read"))],
)
async def list_faq_admin(
    pagination: Pagination,
    filtering: Filtering,
    category: str | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQListResponse:
    """List all FAQ items."""
    service = FAQService(db)
    faqs, total = await service.list_faqs(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        category=category,
        is_published=filtering.is_published,
    )

    return FAQListResponse(
        items=[FAQResponse.model_validate(f) for f in faqs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/faq",
    response_model=FAQResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:create"))],
)
async def create_faq(
    data: FAQCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    """Create a new FAQ item."""
    service = FAQService(db)
    faq = await service.create(tenant_id, data)
    return FAQResponse.model_validate(faq)


@router.get(
    "/admin/faq/{faq_id}",
    response_model=FAQResponse,
    summary="Get FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:read"))],
)
async def get_faq_admin(
    faq_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    """Get FAQ by ID."""
    service = FAQService(db)
    faq = await service.get_by_id(faq_id, tenant_id)
    return FAQResponse.model_validate(faq)


@router.patch(
    "/admin/faq/{faq_id}",
    response_model=FAQResponse,
    summary="Update FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def update_faq(
    faq_id: UUID,
    data: FAQUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    """Update a FAQ item."""
    service = FAQService(db)
    faq = await service.update(faq_id, tenant_id, data)
    return FAQResponse.model_validate(faq)


@router.delete(
    "/admin/faq/{faq_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:delete"))],
)
async def delete_faq(
    faq_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a FAQ item."""
    service = FAQService(db)
    await service.soft_delete(faq_id, tenant_id)


# ============================================================================
# Admin Routes - FAQ Locales
# ============================================================================


@router.post(
    "/admin/faq/{faq_id}/locales",
    response_model=FAQLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def create_faq_locale(
    faq_id: UUID,
    data: FAQLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQLocaleResponse:
    """Add a new locale to a FAQ item."""
    service = FAQService(db)
    locale = await service.create_locale(faq_id, tenant_id, data)
    return FAQLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/faq/{faq_id}/locales/{locale_id}",
    response_model=FAQLocaleResponse,
    summary="Update FAQ locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def update_faq_locale(
    faq_id: UUID,
    locale_id: UUID,
    data: FAQLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQLocaleResponse:
    """Update a FAQ locale."""
    service = FAQService(db)
    locale = await service.update_locale(locale_id, faq_id, tenant_id, data)
    return FAQLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/faq/{faq_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete FAQ locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def delete_faq_locale(
    faq_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from FAQ (minimum 1 locale required)."""
    service = FAQService(db)
    await service.delete_locale(locale_id, faq_id, tenant_id)
