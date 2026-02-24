"""Content module - review service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.core.pagination import paginate_query
from app.modules.content.models import (
    Case,
    Review,
    ReviewAuthorContact,
    ReviewStatus,
)
from app.modules.content.schemas import (
    ReviewAuthorContactCreate,
    ReviewAuthorContactUpdate,
    ReviewCreate,
    ReviewUpdate,
)


class ReviewService(BaseService[Review]):
    """Service for managing reviews."""

    model = Review

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(Review.case).selectinload(Case.locales)]

    async def get_by_id(self, review_id: UUID, tenant_id: UUID) -> Review:
        """Get review by ID."""
        return await self._get_by_id(review_id, tenant_id)

    async def list_reviews(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        case_id: UUID | None = None,
        is_featured: bool | None = None,
    ) -> tuple[list[Review], int]:
        """List reviews with pagination and filters."""
        filters = []
        if status:
            filters.append(Review.status == status)
        if case_id:
            filters.append(Review.case_id == case_id)
        if is_featured is not None:
            filters.append(Review.is_featured == is_featured)

        base_query = self._build_base_query(tenant_id, filters=filters)

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=self._get_default_options(),
            order_by=[Review.sort_order, Review.created_at.desc()],
        )

    async def list_approved(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        case_id: UUID | None = None,
        is_featured: bool | None = None,
    ) -> tuple[list[Review], int]:
        """List approved reviews for public API."""
        filters = [Review.status == ReviewStatus.APPROVED.value]
        if case_id:
            filters.append(Review.case_id == case_id)
        if is_featured is not None:
            filters.append(Review.is_featured == is_featured)

        base_query = self._build_base_query(tenant_id, filters=filters)

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=self._get_default_options(),
            order_by=[Review.sort_order, Review.created_at.desc()],
        )

    async def list_approved_by_case_ids(
        self,
        case_ids: list[UUID],
        tenant_id: UUID,
    ) -> list[Review]:
        """Get approved reviews for multiple cases.
        
        Used for service detail page to show reviews from all related cases.
        """
        if not case_ids:
            return []

        stmt = (
            select(Review)
            .where(Review.tenant_id == tenant_id)
            .where(Review.deleted_at.is_(None))
            .where(Review.status == ReviewStatus.APPROVED.value)
            .where(Review.case_id.in_(case_ids))
            .options(*self._get_default_options())
            .order_by(Review.sort_order, Review.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    @transactional
    async def create(self, tenant_id: UUID, data: ReviewCreate) -> Review:
        """Create a new review."""
        # author_photo_url is set via separate endpoint
        review = Review(
            tenant_id=tenant_id,
            rating=data.rating,
            author_name=data.author_name,
            author_company=data.author_company,
            author_position=data.author_position,
            content=data.content,
            case_id=data.case_id,
            is_featured=data.is_featured,
            source=data.source,
            source_url=data.source_url,
            review_date=data.review_date,
            sort_order=data.sort_order,
            status=ReviewStatus.PENDING.value,
        )
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)

        # Re-fetch with case relationship loaded to avoid lazy loading issues
        return await self.get_by_id(review.id, tenant_id)

    @transactional
    async def update(self, review_id: UUID, tenant_id: UUID, data: ReviewUpdate) -> Review:
        """Update a review."""
        review = await self.get_by_id(review_id, tenant_id)
        review.check_version(data.version)

        # Use model_dump(exclude_unset=True) to get only fields sent in the request
        # (works for both snake_case and camelCase when populate_by_name=True)
        update_data = data.model_dump(exclude_unset=True, exclude={"version"}, by_alias=False)

        # Handle status enum
        if "status" in update_data:
            status_val = update_data["status"]
            if hasattr(status_val, "value"):
                update_data["status"] = status_val.value

        for field, value in update_data.items():
            setattr(review, field, value)

        await self.db.flush()

        # Re-fetch with case relationship loaded to avoid lazy loading issues
        return await self.get_by_id(review_id, tenant_id)

    @transactional
    async def approve(self, review_id: UUID, tenant_id: UUID) -> Review:
        """Approve a review."""
        review = await self.get_by_id(review_id, tenant_id)
        review.approve()
        await self.db.flush()
        # Re-fetch with case relationship loaded
        return await self.get_by_id(review_id, tenant_id)

    @transactional
    async def reject(self, review_id: UUID, tenant_id: UUID) -> Review:
        """Reject a review."""
        review = await self.get_by_id(review_id, tenant_id)
        review.reject()
        await self.db.flush()
        # Re-fetch with case relationship loaded
        return await self.get_by_id(review_id, tenant_id)

    @transactional
    async def update_author_photo_url(
        self, review_id: UUID, tenant_id: UUID, url: str | None
    ) -> "Review":
        """Update or clear the review author photo URL."""
        review = await self.get_by_id(review_id, tenant_id)
        review.author_photo_url = url
        await self.db.flush()
        await self.db.refresh(review)
        return review

    @transactional
    async def soft_delete(self, review_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a review."""
        await self._soft_delete(review_id, tenant_id)

    # ========== Author Contact Management ==========

    @transactional
    async def add_author_contact(
        self, review_id: UUID, tenant_id: UUID, data: ReviewAuthorContactCreate
    ) -> ReviewAuthorContact:
        """Add an author contact to a review."""
        # Verify review exists
        await self.get_by_id(review_id, tenant_id)

        contact = ReviewAuthorContact(
            review_id=review_id,
            contact_type=data.contact_type,
            value=data.value,
            sort_order=data.sort_order,
        )
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    @transactional
    async def update_author_contact(
        self, contact_id: UUID, review_id: UUID, tenant_id: UUID, data: ReviewAuthorContactUpdate
    ) -> ReviewAuthorContact:
        """Update a review author contact."""
        # Verify review exists
        await self.get_by_id(review_id, tenant_id)

        # Get contact
        stmt = select(ReviewAuthorContact).where(
            ReviewAuthorContact.id == contact_id,
            ReviewAuthorContact.review_id == review_id,
        )
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()

        if not contact:
            raise NotFoundError("ReviewAuthorContact", contact_id)

        # Update fields
        if data.contact_type is not None:
            contact.contact_type = data.contact_type
        if data.value is not None:
            contact.value = data.value
        if data.sort_order is not None:
            contact.sort_order = data.sort_order

        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    @transactional
    async def delete_author_contact(
        self, contact_id: UUID, review_id: UUID, tenant_id: UUID
    ) -> None:
        """Delete a review author contact."""
        # Verify review exists
        await self.get_by_id(review_id, tenant_id)

        # Get and delete contact
        stmt = select(ReviewAuthorContact).where(
            ReviewAuthorContact.id == contact_id,
            ReviewAuthorContact.review_id == review_id,
        )
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()

        if not contact:
            raise NotFoundError("ReviewAuthorContact", contact_id)

        await self.db.delete(contact)
        await self.db.flush()
