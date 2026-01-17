"""Integration tests for review repository operations."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Review, ReviewStatus
from app.modules.tenants.models import Tenant


@pytest.mark.integration
class TestReviewRepository:
    """Integration tests for review database operations."""

    @pytest.fixture
    async def tenant(self, db_session: AsyncSession) -> Tenant:
        """Create test tenant."""
        tenant = Tenant(
            id=uuid4(),
            slug=f"test-review-tenant-{uuid4().hex[:8]}",
            name="Test Review Company",
            domain=f"review-{uuid4().hex[:8]}.example.com",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()
        return tenant

    @pytest.fixture
    async def review(self, db_session: AsyncSession, tenant: Tenant) -> Review:
        """Create test review."""
        review = Review(
            id=uuid4(),
            tenant_id=tenant.id,
            author_name="John Doe",
            author_company="Test Corp",
            author_position="CEO",
            content="Excellent service! Highly recommended.",
            rating=5,
            status=ReviewStatus.PENDING.value,
            is_featured=False,
        )
        db_session.add(review)
        await db_session.flush()
        return review

    @pytest.mark.asyncio
    async def test_create_review(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test creating review in database."""
        review = Review(
            tenant_id=tenant.id,
            author_name="Jane Smith",
            author_company="Example Inc",
            content="Great experience!",
            rating=4,
            status=ReviewStatus.PENDING.value,
        )
        db_session.add(review)
        await db_session.flush()

        result = await db_session.execute(
            select(Review).where(Review.id == review.id)
        )
        saved = result.scalar_one()

        assert saved.author_name == "Jane Smith"
        assert saved.rating == 4
        assert saved.status == ReviewStatus.PENDING.value
        assert saved.version == 1

    @pytest.mark.asyncio
    async def test_review_approve(
        self, db_session: AsyncSession, review: Review
    ) -> None:
        """Test approving a review."""
        assert review.status == ReviewStatus.PENDING.value

        review.approve()
        await db_session.flush()

        result = await db_session.execute(
            select(Review).where(Review.id == review.id)
        )
        saved = result.scalar_one()

        assert saved.status == ReviewStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_review_reject(
        self, db_session: AsyncSession, review: Review
    ) -> None:
        """Test rejecting a review."""
        review.reject()
        await db_session.flush()

        result = await db_session.execute(
            select(Review).where(Review.id == review.id)
        )
        saved = result.scalar_one()

        assert saved.status == ReviewStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_review_soft_delete(
        self, db_session: AsyncSession, review: Review
    ) -> None:
        """Test soft delete sets deleted_at."""
        assert review.deleted_at is None

        review.soft_delete()
        await db_session.flush()

        result = await db_session.execute(
            select(Review).where(Review.id == review.id)
        )
        saved = result.scalar_one()

        assert saved.deleted_at is not None

    @pytest.mark.asyncio
    async def test_query_reviews_by_tenant(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test querying reviews by tenant_id."""
        for i in range(3):
            review = Review(
                tenant_id=tenant.id,
                author_name=f"Author {i}",
                content=f"Review content {i}",
                rating=i + 3,
                status=ReviewStatus.PENDING.value,
            )
            db_session.add(review)
        await db_session.flush()

        result = await db_session.execute(
            select(Review)
            .where(Review.tenant_id == tenant.id)
            .where(Review.deleted_at.is_(None))
        )
        reviews = result.scalars().all()

        assert len(reviews) >= 3

    @pytest.mark.asyncio
    async def test_query_approved_reviews(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test querying only approved reviews."""
        # Create pending review
        pending = Review(
            tenant_id=tenant.id,
            author_name="Pending Author",
            content="Pending content",
            rating=4,
            status=ReviewStatus.PENDING.value,
        )
        db_session.add(pending)

        # Create approved review
        approved = Review(
            tenant_id=tenant.id,
            author_name="Approved Author",
            content="Approved content",
            rating=5,
            status=ReviewStatus.APPROVED.value,
        )
        db_session.add(approved)
        await db_session.flush()

        result = await db_session.execute(
            select(Review)
            .where(Review.tenant_id == tenant.id)
            .where(Review.status == ReviewStatus.APPROVED.value)
            .where(Review.deleted_at.is_(None))
        )
        reviews = result.scalars().all()

        assert all(r.status == ReviewStatus.APPROVED.value for r in reviews)

    @pytest.mark.asyncio
    async def test_query_featured_reviews(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test querying featured reviews."""
        # Create non-featured review
        non_featured = Review(
            tenant_id=tenant.id,
            author_name="Regular Author",
            content="Regular content",
            rating=4,
            status=ReviewStatus.APPROVED.value,
            is_featured=False,
        )
        db_session.add(non_featured)

        # Create featured review
        featured = Review(
            tenant_id=tenant.id,
            author_name="Featured Author",
            content="Featured content",
            rating=5,
            status=ReviewStatus.APPROVED.value,
            is_featured=True,
        )
        db_session.add(featured)
        await db_session.flush()

        result = await db_session.execute(
            select(Review)
            .where(Review.tenant_id == tenant.id)
            .where(Review.is_featured.is_(True))
            .where(Review.deleted_at.is_(None))
        )
        reviews = result.scalars().all()

        assert all(r.is_featured for r in reviews)

    @pytest.mark.asyncio
    async def test_review_rating_constraint(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test review rating is within valid range."""
        review = Review(
            tenant_id=tenant.id,
            author_name="Test",
            content="Test content",
            rating=5,
            status=ReviewStatus.PENDING.value,
        )
        db_session.add(review)
        await db_session.flush()

        result = await db_session.execute(
            select(Review).where(Review.id == review.id)
        )
        saved = result.scalar_one()

        assert 1 <= saved.rating <= 5

