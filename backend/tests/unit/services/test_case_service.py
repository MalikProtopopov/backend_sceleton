"""Unit tests for content CaseService."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.content.models import (
    ArticleStatus,
    Case,
    CaseLocale,
    CaseServiceLink,
)
from app.modules.company.models import Service
from app.modules.content.service import CaseService


class TestCaseService:
    """Tests for CaseService - read and write operations."""

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
    def case_service(self, mock_db: AsyncMock) -> CaseService:
        """Create CaseService with mocked dependencies."""
        return CaseService(mock_db)

    @pytest.fixture
    def sample_case(self) -> Case:
        """Create sample case for testing."""
        case = Case(
            id=uuid4(),
            tenant_id=uuid4(),
            status=ArticleStatus.DRAFT.value,
            cover_image_url="https://example.com/case.jpg",
            client_name="Test Client",
            project_year=2024,
            project_duration="3 months",
            is_featured=False,
            sort_order=0,
            version=1,
        )
        case.locales = [
            CaseLocale(
                id=uuid4(),
                case_id=case.id,
                locale="ru",
                slug="test-case",
                title="Тестовый кейс",
                excerpt="Краткое описание",
                description="<p>Полное описание проекта</p>",
                results="<ul><li>Результат 1</li></ul>",
            )
        ]
        case.services = []
        return case

    @pytest.fixture
    def published_case(self, sample_case: Case) -> Case:
        """Create published case."""
        sample_case.status = ArticleStatus.PUBLISHED.value
        sample_case.published_at = datetime.now(UTC)
        return sample_case

    @pytest.fixture
    def sample_service(self) -> Service:
        """Create sample service for linking."""
        return Service(
            id=uuid4(),
            tenant_id=uuid4(),
            icon="icon-web",
            is_published=True,
            sort_order=0,
            version=1,
        )

    # ========== get_by_id Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        sample_case: Case,
    ) -> None:
        """Get by ID should return case when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_case
        mock_db.execute.return_value = mock_result

        case = await case_service.get_by_id(sample_case.id, sample_case.tenant_id)

        assert case.id == sample_case.id
        assert case.client_name == "Test Client"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when case doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await case_service.get_by_id(uuid4(), uuid4())

    # ========== get_by_slug Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_success(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        published_case: Case,
    ) -> None:
        """Get by slug should return published case."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = published_case
        mock_db.execute.return_value = mock_result

        case = await case_service.get_by_slug(
            "test-case", "ru", published_case.tenant_id
        )

        assert case.status == ArticleStatus.PUBLISHED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by slug should raise NotFoundError when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await case_service.get_by_slug("nonexistent", "ru", uuid4())

    # ========== list_cases Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_cases_empty(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
    ) -> None:
        """List cases should return empty list when no cases."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        cases, total = await case_service.list_cases(uuid4())

        assert cases == []
        assert total == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_cases_with_status_filter(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        published_case: Case,
    ) -> None:
        """List cases should filter by status."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [
            published_case
        ]

        mock_db.execute.side_effect = [count_result, list_result]

        cases, total = await case_service.list_cases(
            published_case.tenant_id,
            status="published",
        )

        assert len(cases) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_cases_with_featured_filter(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        sample_case: Case,
    ) -> None:
        """List cases should filter by is_featured."""
        sample_case.is_featured = True

        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [
            sample_case
        ]

        mock_db.execute.side_effect = [count_result, list_result]

        cases, total = await case_service.list_cases(
            sample_case.tenant_id,
            is_featured=True,
        )

        assert len(cases) == 1
        assert cases[0].is_featured is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_cases_with_search(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        sample_case: Case,
    ) -> None:
        """List cases should support search by client_name and title."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [
            sample_case
        ]

        mock_db.execute.side_effect = [count_result, list_result]

        cases, total = await case_service.list_cases(
            sample_case.tenant_id,
            search="Test Client",
        )

        assert len(cases) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_cases_with_pagination(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        sample_case: Case,
    ) -> None:
        """List cases should support pagination."""
        count_result = Mock()
        count_result.scalar.return_value = 25

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = (
            [sample_case] * 10
        )

        mock_db.execute.side_effect = [count_result, list_result]

        cases, total = await case_service.list_cases(
            sample_case.tenant_id,
            page=2,
            page_size=10,
        )

        assert len(cases) == 10
        assert total == 25

    # ========== list_published Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_cases(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        published_case: Case,
    ) -> None:
        """List published should only return published cases for locale."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [
            published_case
        ]

        mock_db.execute.side_effect = [count_result, list_result]

        cases, total = await case_service.list_published(
            published_case.tenant_id, locale="ru"
        )

        assert len(cases) == 1
        assert cases[0].status == ArticleStatus.PUBLISHED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_featured_only(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        published_case: Case,
    ) -> None:
        """List published should filter by is_featured when specified."""
        published_case.is_featured = True

        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [
            published_case
        ]

        mock_db.execute.side_effect = [count_result, list_result]

        cases, total = await case_service.list_published(
            published_case.tenant_id,
            locale="ru",
            is_featured=True,
        )

        assert len(cases) == 1
        assert cases[0].is_featured is True

    # ========== soft_delete Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        sample_case: Case,
    ) -> None:
        """Soft delete should mark case as deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_case
        mock_db.execute.return_value = mock_result

        assert sample_case.deleted_at is None

        await case_service.soft_delete(sample_case.id, sample_case.tenant_id)

        assert sample_case.deleted_at is not None
        mock_db.flush.assert_called()

    # ========== Service Links Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_with_service_links(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        sample_case: Case,
        sample_service: Service,
    ) -> None:
        """Case should be able to have linked services."""
        link = CaseServiceLink(
            id=uuid4(),
            case_id=sample_case.id,
            service_id=sample_service.id,
        )
        link.service = sample_service
        sample_case.services = [link]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_case
        mock_db.execute.return_value = mock_result

        case = await case_service.get_by_id(sample_case.id, sample_case.tenant_id)

        assert len(case.services) == 1
        assert case.services[0].service_id == sample_service.id

    # ========== Status Transitions Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_status_draft(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        sample_case: Case,
    ) -> None:
        """Draft case should not have published_at."""
        assert sample_case.status == ArticleStatus.DRAFT.value
        assert sample_case.published_at is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_case_status_published(
        self,
        case_service: CaseService,
        mock_db: AsyncMock,
        published_case: Case,
    ) -> None:
        """Published case should have published_at set."""
        assert published_case.status == ArticleStatus.PUBLISHED.value
        assert published_case.published_at is not None
