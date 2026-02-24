"""Unit tests for content TopicService and FAQService."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.content.models import Topic, TopicLocale, FAQ, FAQLocale
from app.modules.content.services import TopicService, FAQService


class TestTopicService:
    """Tests for TopicService - CRUD operations."""

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
    def topic_service(self, mock_db: AsyncMock) -> TopicService:
        """Create TopicService with mocked dependencies."""
        return TopicService(mock_db)

    @pytest.fixture
    def sample_topic(self) -> Topic:
        """Create sample topic for testing."""
        topic = Topic(
            id=uuid4(),
            tenant_id=uuid4(),
            icon="icon-tech",
            color="#FF5500",
            sort_order=0,
            version=1,
        )
        topic.locales = [
            TopicLocale(
                id=uuid4(),
                topic_id=topic.id,
                locale="ru",
                slug="technology",
                title="Технологии",
                description="Статьи о технологиях",
            )
        ]
        return topic

    # ========== get_by_id Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        topic_service: TopicService,
        mock_db: AsyncMock,
        sample_topic: Topic,
    ) -> None:
        """Get by ID should return topic when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_topic
        mock_db.execute.return_value = mock_result

        topic = await topic_service.get_by_id(sample_topic.id, sample_topic.tenant_id)

        assert topic.id == sample_topic.id
        assert topic.icon == "icon-tech"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        topic_service: TopicService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when topic doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await topic_service.get_by_id(uuid4(), uuid4())

    # ========== list_topics Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_topics_empty(
        self,
        topic_service: TopicService,
        mock_db: AsyncMock,
    ) -> None:
        """List topics should return empty list when no topics."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        topics = await topic_service.list_topics(uuid4())

        assert topics == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_topics_returns_all(
        self,
        topic_service: TopicService,
        mock_db: AsyncMock,
        sample_topic: Topic,
    ) -> None:
        """List topics should return all topics for tenant."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_topic]
        mock_db.execute.return_value = mock_result

        topics = await topic_service.list_topics(sample_topic.tenant_id)

        assert len(topics) == 1

    # ========== soft_delete Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        topic_service: TopicService,
        mock_db: AsyncMock,
        sample_topic: Topic,
    ) -> None:
        """Soft delete should mark topic as deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_topic
        mock_db.execute.return_value = mock_result

        assert sample_topic.deleted_at is None

        await topic_service.soft_delete(sample_topic.id, sample_topic.tenant_id)

        assert sample_topic.deleted_at is not None


class TestFAQService:
    """Tests for FAQService - CRUD operations."""

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
    def faq_service(self, mock_db: AsyncMock) -> FAQService:
        """Create FAQService with mocked dependencies."""
        return FAQService(mock_db)

    @pytest.fixture
    def sample_faq(self) -> FAQ:
        """Create sample FAQ for testing."""
        faq = FAQ(
            id=uuid4(),
            tenant_id=uuid4(),
            category="General",
            is_published=True,
            sort_order=0,
            version=1,
        )
        faq.locales = [
            FAQLocale(
                id=uuid4(),
                faq_id=faq.id,
                locale="ru",
                question="Как оформить заказ?",
                answer="<p>Свяжитесь с нами...</p>",
            )
        ]
        return faq

    @pytest.fixture
    def unpublished_faq(self, sample_faq: FAQ) -> FAQ:
        """Create unpublished FAQ."""
        sample_faq.is_published = False
        return sample_faq

    # ========== get_by_id Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        faq_service: FAQService,
        mock_db: AsyncMock,
        sample_faq: FAQ,
    ) -> None:
        """Get by ID should return FAQ when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_faq
        mock_db.execute.return_value = mock_result

        faq = await faq_service.get_by_id(sample_faq.id, sample_faq.tenant_id)

        assert faq.id == sample_faq.id
        assert faq.category == "General"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        faq_service: FAQService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when FAQ doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await faq_service.get_by_id(uuid4(), uuid4())

    # ========== list_faqs Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_faqs_empty(
        self,
        faq_service: FAQService,
        mock_db: AsyncMock,
    ) -> None:
        """List FAQs should return empty list when no FAQs."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        faqs, total = await faq_service.list_faqs(uuid4())

        assert faqs == []
        assert total == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_faqs_with_category_filter(
        self,
        faq_service: FAQService,
        mock_db: AsyncMock,
        sample_faq: FAQ,
    ) -> None:
        """List FAQs should filter by category."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_faq]
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result

        faqs, total = await faq_service.list_faqs(
            sample_faq.tenant_id,
            category="General",
        )

        assert len(faqs) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_faqs_with_published_filter(
        self,
        faq_service: FAQService,
        mock_db: AsyncMock,
        sample_faq: FAQ,
    ) -> None:
        """List FAQs should filter by is_published."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_faq]
        mock_result.scalar.return_value = 1
        mock_db.execute.return_value = mock_result

        faqs, total = await faq_service.list_faqs(
            sample_faq.tenant_id,
            is_published=True,
        )

        assert len(faqs) == 1
        assert faqs[0].is_published is True

    # ========== list_published Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_faqs(
        self,
        faq_service: FAQService,
        mock_db: AsyncMock,
        sample_faq: FAQ,
    ) -> None:
        """List published should only return published FAQs for locale."""
        mock_result = Mock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = [
            sample_faq
        ]
        mock_db.execute.return_value = mock_result

        faqs = await faq_service.list_published(sample_faq.tenant_id, locale="ru")

        assert len(faqs) == 1
        assert faqs[0].is_published is True

    # ========== soft_delete Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        faq_service: FAQService,
        mock_db: AsyncMock,
        sample_faq: FAQ,
    ) -> None:
        """Soft delete should mark FAQ as deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_faq
        mock_db.execute.return_value = mock_result

        assert sample_faq.deleted_at is None

        await faq_service.soft_delete(sample_faq.id, sample_faq.tenant_id)

        assert sample_faq.deleted_at is not None
