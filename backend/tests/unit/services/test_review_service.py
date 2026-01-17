"""Unit tests for review service - read operations."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.content.models import Review, ReviewStatus
from app.modules.content.service import ReviewService


class TestReviewService:
    """Tests for ReviewService - read-only operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        return db

    @pytest.fixture
    def review_service(self, mock_db: AsyncMock) -> ReviewService:
        """Create ReviewService with mocked dependencies."""
        return ReviewService(mock_db)

    @pytest.fixture
    def sample_review(self) -> Review:
        """Create sample review for testing."""
        return Review(
            id=uuid4(),
            tenant_id=uuid4(),
            author_name="John Doe",
            author_company="Test Corp",
            author_position="CEO",
            content="Great service! Highly recommended.",
            rating=5,
            status=ReviewStatus.PENDING.value,
            is_featured=False,
            version=1,
        )

    @pytest.fixture
    def approved_review(self, sample_review: Review) -> Review:
        """Create approved review."""
        sample_review.status = ReviewStatus.APPROVED.value
        return sample_review

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
        sample_review: Review,
    ) -> None:
        """Get by ID should return review when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_review
        mock_db.execute.return_value = mock_result

        review = await review_service.get_by_id(sample_review.id, sample_review.tenant_id)

        assert review.id == sample_review.id
        assert review.author_name == sample_review.author_name

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when review doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await review_service.get_by_id(uuid4(), uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_reviews_empty(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
    ) -> None:
        """List reviews should return empty list when no reviews."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        reviews, total = await review_service.list_reviews(uuid4())

        assert reviews == []
        assert total == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_reviews_with_status_filter(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
        sample_review: Review,
    ) -> None:
        """List reviews should filter by status."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_review]

        mock_db.execute.side_effect = [count_result, list_result]

        reviews, total = await review_service.list_reviews(
            sample_review.tenant_id,
            status=ReviewStatus.PENDING.value,
        )

        assert len(reviews) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_reviews_with_pagination(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
        sample_review: Review,
    ) -> None:
        """List reviews should support pagination."""
        count_result = Mock()
        count_result.scalar.return_value = 50

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_review] * 20

        mock_db.execute.side_effect = [count_result, list_result]

        reviews, total = await review_service.list_reviews(
            sample_review.tenant_id,
            page=1,
            page_size=20,
        )

        assert len(reviews) == 20
        assert total == 50

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_reviews_by_case_id(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
        sample_review: Review,
    ) -> None:
        """List reviews should filter by case_id."""
        case_id = uuid4()
        sample_review.case_id = case_id

        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_review]

        mock_db.execute.side_effect = [count_result, list_result]

        reviews, total = await review_service.list_reviews(
            sample_review.tenant_id,
            case_id=case_id,
        )

        assert len(reviews) == 1
        assert reviews[0].case_id == case_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_approved_returns_only_approved(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
        approved_review: Review,
    ) -> None:
        """List approved should only return approved reviews."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [approved_review]

        mock_db.execute.side_effect = [count_result, list_result]

        reviews, total = await review_service.list_approved(approved_review.tenant_id)

        assert len(reviews) == 1
        assert all(r.status == ReviewStatus.APPROVED.value for r in reviews)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_featured_reviews(
        self,
        review_service: ReviewService,
        mock_db: AsyncMock,
        approved_review: Review,
    ) -> None:
        """List approved should filter by is_featured."""
        approved_review.is_featured = True

        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [approved_review]

        mock_db.execute.side_effect = [count_result, list_result]

        reviews, total = await review_service.list_approved(
            approved_review.tenant_id,
            is_featured=True,
        )

        assert len(reviews) == 1
        assert all(r.is_featured for r in reviews)

    @pytest.mark.unit
    def test_review_status_enum_values(self) -> None:
        """Review status enum should have correct values."""
        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.APPROVED.value == "approved"
        assert ReviewStatus.REJECTED.value == "rejected"

    @pytest.mark.unit
    def test_review_rating_valid_range(self, sample_review: Review) -> None:
        """Review rating should be within valid range."""
        assert 1 <= sample_review.rating <= 5

    @pytest.mark.unit
    def test_review_default_values(self, sample_review: Review) -> None:
        """Review should have expected default values."""
        assert sample_review.is_featured is False
        assert sample_review.version == 1
