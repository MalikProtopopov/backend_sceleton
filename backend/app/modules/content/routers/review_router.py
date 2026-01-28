"""Review routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.content.mappers import map_case_to_minimal_response
from app.modules.content.models import Case, CaseLocale
from app.modules.content.schemas import (
    ReviewCreate,
    ReviewListResponse,
    ReviewPublicListResponse,
    ReviewPublicResponse,
    ReviewResponse,
    ReviewUpdate,
)
from app.modules.content.service import CaseService, ReviewService

router = APIRouter()


# ============================================================================
# Public Routes - Reviews
# ============================================================================


@router.get(
    "/public/reviews",
    response_model=ReviewPublicListResponse,
    summary="List approved reviews",
    tags=["Public - Content"],
)
async def list_reviews_public(
    pagination: Pagination,
    locale: Locale,
    tenant_id: PublicTenantId,
    case_id: UUID | None = Query(default=None, alias="caseId"),
    featured: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ReviewPublicListResponse:
    """List approved reviews for public display."""
    service = ReviewService(db)
    reviews, total = await service.list_approved(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        case_id=case_id,
        is_featured=featured,
    )

    items = []
    for r in reviews:
        case_data = None
        if r.case:
            case_data = map_case_to_minimal_response(r.case, locale.locale)
        
        items.append(ReviewPublicResponse(
            id=r.id,
            rating=r.rating,
            author_name=r.author_name,
            author_company=r.author_company,
            author_position=r.author_position,
            author_photo_url=r.author_photo_url,
            content=r.content,
            source=r.source,
            review_date=r.review_date,
            case=case_data,
        ))

    return ReviewPublicListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ============================================================================
# Admin Routes - Reviews
# ============================================================================


@router.get(
    "/admin/reviews",
    response_model=ReviewListResponse,
    summary="List reviews (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:read"))],
)
async def list_reviews_admin(
    pagination: Pagination,
    review_status: str | None = Query(default=None, alias="status"),
    case_id: UUID | None = Query(default=None, alias="caseId"),
    case_slug: str | None = Query(default=None, alias="caseSlug", description="Filter by case slug"),
    featured: bool | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewListResponse:
    """List all reviews with filters."""
    # If case_slug provided and case_id is not, find the case
    if case_slug and not case_id:
        stmt = (
            select(Case)
            .join(CaseLocale)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(CaseLocale.slug == case_slug)
            .limit(1)
        )
        result = await db.execute(stmt)
        case = result.scalar_one_or_none()
        if case:
            case_id = case.id
    
    service = ReviewService(db)
    reviews, total = await service.list_reviews(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=review_status,
        case_id=case_id,
        is_featured=featured,
    )

    items = []
    for r in reviews:
        review_dict = {
            "rating": r.rating,
            "author_name": r.author_name,
            "author_company": r.author_company,
            "author_position": r.author_position,
            "content": r.content,
            "is_featured": r.is_featured,
            "source": r.source,
            "source_url": r.source_url,
            "review_date": r.review_date,
            "sort_order": r.sort_order,
            "id": r.id,
            "tenant_id": r.tenant_id,
            "author_photo_url": r.author_photo_url,
            "status": r.status,
            "case_id": r.case_id,
            "case": None,
            "version": r.version,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "deleted_at": r.deleted_at,
        }
        if r.case and r.case.locales:
            locale = r.case.locales[0].locale if r.case.locales else "ru"
            review_dict["case"] = map_case_to_minimal_response(r.case, locale)
        items.append(ReviewResponse(**review_dict))

    return ReviewListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:create"))],
)
async def create_review(
    data: ReviewCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Create a new review."""
    service = ReviewService(db)
    review = await service.create(tenant_id, data)
    return ReviewResponse.model_validate(review)


@router.get(
    "/admin/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Get review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:read"))],
)
async def get_review_admin(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Get review by ID."""
    service = ReviewService(db)
    review = await service.get_by_id(review_id, tenant_id)
    return ReviewResponse.model_validate(review)


@router.patch(
    "/admin/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Update a review."""
    service = ReviewService(db)
    review = await service.update(review_id, tenant_id, data)
    return ReviewResponse.model_validate(review)


@router.post(
    "/admin/reviews/{review_id}/approve",
    response_model=ReviewResponse,
    summary="Approve review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def approve_review(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Approve a review for public display."""
    service = ReviewService(db)
    review = await service.approve(review_id, tenant_id)
    return ReviewResponse.model_validate(review)


@router.post(
    "/admin/reviews/{review_id}/reject",
    response_model=ReviewResponse,
    summary="Reject review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def reject_review(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Reject a review."""
    service = ReviewService(db)
    review = await service.reject(review_id, tenant_id)
    return ReviewResponse.model_validate(review)


@router.delete(
    "/admin/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:delete"))],
)
async def delete_review(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a review."""
    service = ReviewService(db)
    await service.soft_delete(review_id, tenant_id)


@router.post(
    "/admin/reviews/{review_id}/author-photo",
    response_model=ReviewResponse,
    summary="Upload review author photo",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def upload_review_author_photo(
    review_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Upload or replace author photo for review."""
    service = ReviewService(db)
    review = await service.get_by_id(review_id, tenant_id)
    
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="reviews",
        entity_id=review_id,
        old_image_url=review.author_photo_url,
    )
    
    review.author_photo_url = new_url
    await db.commit()
    review = await service.get_by_id(review_id, tenant_id)
    
    return ReviewResponse.model_validate(review)


@router.delete(
    "/admin/reviews/{review_id}/author-photo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review author photo",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def delete_review_author_photo(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete author photo from review."""
    service = ReviewService(db)
    review = await service.get_by_id(review_id, tenant_id)
    
    if review.author_photo_url:
        await image_upload_service.delete_image(review.author_photo_url)
        review.author_photo_url = None
        await db.commit()
