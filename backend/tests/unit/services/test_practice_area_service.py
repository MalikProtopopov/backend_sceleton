"""Unit tests for company PracticeAreaService."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.company.models import PracticeArea, PracticeAreaLocale
from app.modules.company.service import PracticeAreaService


class TestPracticeAreaService:
    """Tests for PracticeAreaService - CRUD operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.delete = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def practice_area_service(self, mock_db: AsyncMock) -> PracticeAreaService:
        """Create PracticeAreaService with mocked dependencies."""
        return PracticeAreaService(mock_db)

    @pytest.fixture
    def sample_practice_area(self) -> PracticeArea:
        """Create sample practice area for testing."""
        pa = PracticeArea(
            id=uuid4(),
            tenant_id=uuid4(),
            icon="icon-fintech",
            is_published=True,
            sort_order=0,
            version=1,
        )
        pa.locales = [
            PracticeAreaLocale(
                id=uuid4(),
                practice_area_id=pa.id,
                locale="ru",
                slug="fintech",
                title="FinTech",
                description="Финансовые технологии",
            )
        ]
        return pa

    @pytest.fixture
    def unpublished_practice_area(self, sample_practice_area: PracticeArea) -> PracticeArea:
        """Create unpublished practice area."""
        sample_practice_area.is_published = False
        return sample_practice_area

    # ========== get_by_id Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
        sample_practice_area: PracticeArea,
    ) -> None:
        """Get by ID should return practice area when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_practice_area
        mock_db.execute.return_value = mock_result

        pa = await practice_area_service.get_by_id(
            sample_practice_area.id, sample_practice_area.tenant_id
        )

        assert pa.id == sample_practice_area.id
        assert pa.icon == "icon-fintech"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when practice area doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await practice_area_service.get_by_id(uuid4(), uuid4())

    # ========== list_all Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_all_empty(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
    ) -> None:
        """List all should return empty list when no practice areas."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        practice_areas = await practice_area_service.list_all(uuid4())

        assert practice_areas == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_all_returns_all(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
        sample_practice_area: PracticeArea,
    ) -> None:
        """List all should return all practice areas for tenant."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_practice_area]
        mock_db.execute.return_value = mock_result

        practice_areas = await practice_area_service.list_all(
            sample_practice_area.tenant_id
        )

        assert len(practice_areas) == 1

    # ========== list_published Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_practice_areas(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
        sample_practice_area: PracticeArea,
    ) -> None:
        """List published should only return published practice areas for locale."""
        mock_result = Mock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = [
            sample_practice_area
        ]
        mock_db.execute.return_value = mock_result

        practice_areas = await practice_area_service.list_published(
            sample_practice_area.tenant_id, locale="ru"
        )

        assert len(practice_areas) == 1
        assert practice_areas[0].is_published is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_excludes_unpublished(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
    ) -> None:
        """List published should not return unpublished practice areas."""
        mock_result = Mock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        practice_areas = await practice_area_service.list_published(uuid4(), locale="ru")

        assert practice_areas == []

    # ========== soft_delete Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
        sample_practice_area: PracticeArea,
    ) -> None:
        """Soft delete should mark practice area as deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_practice_area
        mock_db.execute.return_value = mock_result

        assert sample_practice_area.deleted_at is None

        await practice_area_service.soft_delete(
            sample_practice_area.id, sample_practice_area.tenant_id
        )

        assert sample_practice_area.deleted_at is not None
        mock_db.flush.assert_called()

    # ========== Locale Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_practice_area_has_locales(
        self,
        practice_area_service: PracticeAreaService,
        mock_db: AsyncMock,
        sample_practice_area: PracticeArea,
    ) -> None:
        """Practice area should have localized content."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_practice_area
        mock_db.execute.return_value = mock_result

        pa = await practice_area_service.get_by_id(
            sample_practice_area.id, sample_practice_area.tenant_id
        )

        assert len(pa.locales) == 1
        assert pa.locales[0].locale == "ru"
        assert pa.locales[0].title == "FinTech"
