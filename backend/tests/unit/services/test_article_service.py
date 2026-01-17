"""Unit tests for article service - read operations."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.content.models import Article, ArticleLocale, ArticleStatus
from app.modules.content.service import ArticleService


class TestArticleService:
    """Tests for ArticleService - read-only operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.delete = AsyncMock()
        return db

    @pytest.fixture
    def article_service(self, mock_db: AsyncMock) -> ArticleService:
        """Create ArticleService with mocked dependencies."""
        return ArticleService(mock_db)

    @pytest.fixture
    def sample_article(self) -> Article:
        """Create sample article for testing."""
        article = Article(
            id=uuid4(),
            tenant_id=uuid4(),
            status=ArticleStatus.DRAFT.value,
            cover_image_url="https://example.com/image.jpg",
            view_count=0,
            version=1,
        )
        article.locales = [
            ArticleLocale(
                id=uuid4(),
                article_id=article.id,
                locale="en",
                slug="test-article",
                title="Test Article",
                excerpt="Test excerpt",
                content="Test content",
            )
        ]
        article.topics = []
        return article

    @pytest.fixture
    def published_article(self, sample_article: Article) -> Article:
        """Create published article."""
        sample_article.status = ArticleStatus.PUBLISHED.value
        sample_article.published_at = datetime.utcnow()
        return sample_article

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
        sample_article: Article,
    ) -> None:
        """Get by ID should return article when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_article
        mock_db.execute.return_value = mock_result

        article = await article_service.get_by_id(sample_article.id, sample_article.tenant_id)

        assert article.id == sample_article.id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when article doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await article_service.get_by_id(uuid4(), uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_success(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
        published_article: Article,
    ) -> None:
        """Get by slug should return published article."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = published_article
        mock_db.execute.return_value = mock_result

        article = await article_service.get_by_slug(
            "test-article", "en", published_article.tenant_id
        )

        assert article.status == ArticleStatus.PUBLISHED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by slug should raise NotFoundError when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await article_service.get_by_slug("nonexistent", "en", uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_articles_empty(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
    ) -> None:
        """List articles should return empty list when no articles."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        articles, total = await article_service.list_articles(uuid4())

        assert articles == []
        assert total == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_articles_with_status_filter(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
        sample_article: Article,
    ) -> None:
        """List articles should filter by status."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_article]

        mock_db.execute.side_effect = [count_result, list_result]

        articles, total = await article_service.list_articles(
            sample_article.tenant_id,
            status="draft",
        )

        assert len(articles) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_articles_with_pagination(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
        sample_article: Article,
    ) -> None:
        """List articles should support pagination."""
        count_result = Mock()
        count_result.scalar.return_value = 25

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_article] * 10

        mock_db.execute.side_effect = [count_result, list_result]

        articles, total = await article_service.list_articles(
            sample_article.tenant_id,
            page=2,
            page_size=10,
        )

        assert len(articles) == 10
        assert total == 25

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_articles(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
        published_article: Article,
    ) -> None:
        """List published should only return published articles."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [published_article]

        mock_db.execute.side_effect = [count_result, list_result]

        articles, total = await article_service.list_published(
            published_article.tenant_id, locale="en"
        )

        assert len(articles) == 1
        assert articles[0].status == ArticleStatus.PUBLISHED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_increment_view_count(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
        sample_article: Article,
    ) -> None:
        """Increment view should increase view_count by 1."""
        original_count = sample_article.view_count

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_article
        mock_db.execute.return_value = mock_result

        await article_service.increment_view(sample_article.id, sample_article.tenant_id)

        assert sample_article.view_count == original_count + 1
        mock_db.commit.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_slug_unique_available(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
    ) -> None:
        """Check slug should pass when slug is available."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Should not raise
        await article_service._check_slug_unique(uuid4(), "new-slug", "en")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_slug_unique_taken(
        self,
        article_service: ArticleService,
        mock_db: AsyncMock,
        sample_article: Article,
    ) -> None:
        """Check slug should raise error when slug is taken."""
        from app.core.exceptions import SlugAlreadyExistsError

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_article.locales[0]
        mock_db.execute.return_value = mock_result

        with pytest.raises(SlugAlreadyExistsError):
            await article_service._check_slug_unique(
                sample_article.tenant_id, "test-article", "en"
            )
