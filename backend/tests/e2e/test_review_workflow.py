"""E2E tests for review moderation workflow."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Review, ReviewStatus
from app.modules.tenants.models import Tenant


@pytest.mark.e2e
class TestReviewModerationWorkflow:
    """E2E tests for review moderation lifecycle."""

    @pytest.fixture
    async def tenant(self, db_session: AsyncSession) -> Tenant:
        """Create test tenant."""
        tenant = Tenant(
            id=uuid4(),
            slug=f"e2e-review-{uuid4().hex[:8]}",
            name="E2E Review Test",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()
        return tenant

    @pytest.mark.asyncio
    async def test_review_submission_to_approval(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test complete workflow: submit review -> approve."""
        # Step 1: Create pending review (simulating customer submission)
        review = Review(
            id=uuid4(),
            tenant_id=tenant.id,
            author_name="Happy Customer",
            author_company="Great Corp",
            author_position="CEO",
            content="Excellent service! Would recommend to everyone.",
            rating=5,
            status=ReviewStatus.PENDING.value,
            is_featured=False,
        )
        db_session.add(review)
        await db_session.flush()

        assert review.status == ReviewStatus.PENDING.value

        # Step 2: Admin approves the review
        review.approve()
        await db_session.flush()

        # Verify approval
        result = await db_session.execute(
            select(Review).where(Review.id == review.id)
        )
        saved = result.scalar_one()

        assert saved.status == ReviewStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_review_submission_to_rejection(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test workflow: submit review -> reject."""
        review = Review(
            tenant_id=tenant.id,
            author_name="Spam User",
            content="Buy cheap products at spamsite.com!",
            rating=1,
            status=ReviewStatus.PENDING.value,
        )
        db_session.add(review)
        await db_session.flush()

        # Admin rejects spam review
        review.reject()
        await db_session.flush()

        result = await db_session.execute(
            select(Review).where(Review.id == review.id)
        )
        saved = result.scalar_one()

        assert saved.status == ReviewStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_review_featured_flag(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test marking review as featured."""
        review = Review(
            tenant_id=tenant.id,
            author_name="VIP Client",
            content="Amazing partnership!",
            rating=5,
            status=ReviewStatus.APPROVED.value,
            is_featured=False,
        )
        db_session.add(review)
        await db_session.flush()

        # Mark as featured
        review.is_featured = True
        await db_session.flush()

        # Query featured reviews
        result = await db_session.execute(
            select(Review)
            .where(Review.tenant_id == tenant.id)
            .where(Review.is_featured.is_(True))
        )
        featured = result.scalars().all()

        assert len(featured) >= 1
        assert all(r.is_featured for r in featured)

    @pytest.mark.asyncio
    async def test_multiple_reviews_moderation(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test moderating multiple reviews in batch."""
        # Create several pending reviews
        reviews = []
        for i in range(5):
            review = Review(
                tenant_id=tenant.id,
                author_name=f"Customer {i}",
                content=f"Review content {i}",
                rating=4 + (i % 2),
                status=ReviewStatus.PENDING.value,
            )
            db_session.add(review)
            reviews.append(review)

        await db_session.flush()

        # Approve first 3, reject last 2
        for i, review in enumerate(reviews):
            if i < 3:
                review.approve()
            else:
                review.reject()

        await db_session.flush()

        # Count by status
        approved_result = await db_session.execute(
            select(Review)
            .where(Review.tenant_id == tenant.id)
            .where(Review.status == ReviewStatus.APPROVED.value)
        )
        approved = approved_result.scalars().all()

        rejected_result = await db_session.execute(
            select(Review)
            .where(Review.tenant_id == tenant.id)
            .where(Review.status == ReviewStatus.REJECTED.value)
        )
        rejected = rejected_result.scalars().all()

        assert len(approved) >= 3
        assert len(rejected) >= 2

    @pytest.mark.asyncio
    async def test_review_soft_delete(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test soft deleting a review."""
        review = Review(
            tenant_id=tenant.id,
            author_name="To Delete",
            content="This will be deleted",
            rating=3,
            status=ReviewStatus.APPROVED.value,
        )
        db_session.add(review)
        await db_session.flush()

        review_id = review.id

        # Soft delete
        review.soft_delete()
        await db_session.flush()

        # Should not appear in active queries
        active_result = await db_session.execute(
            select(Review)
            .where(Review.id == review_id)
            .where(Review.deleted_at.is_(None))
        )
        active = active_result.scalar_one_or_none()

        assert active is None

