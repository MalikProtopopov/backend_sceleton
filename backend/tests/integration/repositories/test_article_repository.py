"""Integration tests for article repository operations."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Article, ArticleLocale, ArticleStatus
from app.modules.content.service import ArticleService
from app.modules.tenants.models import Tenant


@pytest.mark.integration
class TestArticleRepository:
    """Integration tests for article database operations."""

    @pytest.fixture
    async def tenant(self, db_session: AsyncSession) -> Tenant:
        """Create test tenant."""
        tenant = Tenant(
            id=uuid4(),
            slug=f"test-tenant-{uuid4().hex[:8]}",
            name="Test Company",
            domain=f"test-{uuid4().hex[:8]}.example.com",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()
        return tenant

    @pytest.fixture
    async def article(self, db_session: AsyncSession, tenant: Tenant) -> Article:
        """Create test article."""
        article = Article(
            id=uuid4(),
            tenant_id=tenant.id,
            status=ArticleStatus.DRAFT.value,
            cover_image_url="https://example.com/image.jpg",
            view_count=0,
        )
        db_session.add(article)
        await db_session.flush()

        locale = ArticleLocale(
            id=uuid4(),
            article_id=article.id,
            locale="en",
            slug="test-article",
            title="Test Article",
            excerpt="Test excerpt",
            content="Test content body",
        )
        db_session.add(locale)
        await db_session.flush()
        return article

    @pytest.mark.asyncio
    async def test_create_article(self, db_session: AsyncSession, tenant: Tenant) -> None:
        """Test creating article in database."""
        article = Article(
            tenant_id=tenant.id,
            status=ArticleStatus.DRAFT.value,
            cover_image_url="https://example.com/cover.jpg",
        )
        db_session.add(article)
        await db_session.flush()

        # Verify article was created
        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        assert saved.id == article.id
        assert saved.tenant_id == tenant.id
        assert saved.status == ArticleStatus.DRAFT.value
        assert saved.version == 1

    @pytest.mark.asyncio
    async def test_article_with_locale(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test creating article with locale data."""
        article = Article(
            tenant_id=tenant.id,
            status=ArticleStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.flush()

        locale = ArticleLocale(
            article_id=article.id,
            locale="ru",
            slug="test-article-ru",
            title="Тестовая статья",
            excerpt="Краткое описание",
            content="Содержание статьи",
        )
        db_session.add(locale)
        await db_session.flush()

        # Verify locale was created
        result = await db_session.execute(
            select(ArticleLocale).where(ArticleLocale.article_id == article.id)
        )
        saved_locale = result.scalar_one()

        assert saved_locale.locale == "ru"
        assert saved_locale.title == "Тестовая статья"
        assert saved_locale.slug == "test-article-ru"

    @pytest.mark.asyncio
    async def test_article_soft_delete(
        self, db_session: AsyncSession, article: Article
    ) -> None:
        """Test soft delete sets deleted_at."""
        assert article.deleted_at is None

        article.soft_delete()
        await db_session.flush()

        # Verify soft delete
        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        assert saved.deleted_at is not None

    @pytest.mark.asyncio
    async def test_article_publish(
        self, db_session: AsyncSession, article: Article
    ) -> None:
        """Test publishing article sets status and published_at."""
        assert article.status == ArticleStatus.DRAFT.value
        assert article.published_at is None

        article.publish()
        await db_session.flush()

        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        assert saved.status == ArticleStatus.PUBLISHED.value
        assert saved.published_at is not None

    @pytest.mark.asyncio
    async def test_article_unpublish(
        self, db_session: AsyncSession, article: Article
    ) -> None:
        """Test unpublishing article reverts to draft."""
        article.publish()
        await db_session.flush()

        article.unpublish()
        await db_session.flush()

        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        assert saved.status == ArticleStatus.DRAFT.value

    @pytest.mark.asyncio
    async def test_article_version_exists(
        self, db_session: AsyncSession, article: Article
    ) -> None:
        """Test article has version for optimistic locking."""
        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        # Version should be positive integer
        assert saved.version >= 1

    @pytest.mark.asyncio
    async def test_query_articles_by_tenant(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test querying articles by tenant_id."""
        # Create multiple articles
        for i in range(3):
            article = Article(
                tenant_id=tenant.id,
                status=ArticleStatus.DRAFT.value,
            )
            db_session.add(article)
        await db_session.flush()

        # Query
        result = await db_session.execute(
            select(Article)
            .where(Article.tenant_id == tenant.id)
            .where(Article.deleted_at.is_(None))
        )
        articles = result.scalars().all()

        assert len(articles) >= 3

    @pytest.mark.asyncio
    async def test_query_articles_by_status(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test querying articles by status."""
        # Create draft article
        draft = Article(tenant_id=tenant.id, status=ArticleStatus.DRAFT.value)
        db_session.add(draft)

        # Create published article
        published = Article(
            tenant_id=tenant.id,
            status=ArticleStatus.PUBLISHED.value,
            published_at=datetime.utcnow(),
        )
        db_session.add(published)
        await db_session.flush()

        # Query published only
        result = await db_session.execute(
            select(Article)
            .where(Article.tenant_id == tenant.id)
            .where(Article.status == ArticleStatus.PUBLISHED.value)
            .where(Article.deleted_at.is_(None))
        )
        articles = result.scalars().all()

        assert all(a.status == ArticleStatus.PUBLISHED.value for a in articles)

