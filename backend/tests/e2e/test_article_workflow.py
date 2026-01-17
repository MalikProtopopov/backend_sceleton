"""E2E tests for article publishing workflow."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Article, ArticleLocale, ArticleStatus
from app.modules.tenants.models import Tenant


@pytest.mark.e2e
class TestArticleWorkflow:
    """E2E tests for complete article lifecycle."""

    @pytest.fixture
    async def tenant(self, db_session: AsyncSession) -> Tenant:
        """Create test tenant."""
        tenant = Tenant(
            id=uuid4(),
            slug=f"e2e-article-{uuid4().hex[:8]}",
            name="E2E Article Test",
            is_active=True,
        )
        db_session.add(tenant)
        await db_session.flush()
        return tenant

    @pytest.mark.asyncio
    async def test_article_create_to_publish_workflow(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test complete workflow: create draft -> add content -> publish."""
        # Step 1: Create draft article
        article = Article(
            id=uuid4(),
            tenant_id=tenant.id,
            status=ArticleStatus.DRAFT.value,
            cover_image_url="https://example.com/cover.jpg",
        )
        db_session.add(article)
        await db_session.flush()

        assert article.status == ArticleStatus.DRAFT.value
        assert article.published_at is None

        # Step 2: Add locale content
        locale_en = ArticleLocale(
            id=uuid4(),
            article_id=article.id,
            locale="en",
            slug="test-article-e2e",
            title="E2E Test Article",
            excerpt="This is a test article",
            content="Full content here...",
            meta_title="E2E Test | My Site",
            meta_description="Test article description",
        )
        db_session.add(locale_en)
        await db_session.flush()

        # Step 3: Add Russian locale
        locale_ru = ArticleLocale(
            id=uuid4(),
            article_id=article.id,
            locale="ru",
            slug="test-statya-e2e",
            title="E2E Тестовая статья",
            excerpt="Это тестовая статья",
            content="Полное содержание...",
        )
        db_session.add(locale_ru)
        await db_session.flush()

        # Step 4: Publish article
        article.publish()
        await db_session.flush()

        # Verify final state
        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved_article = result.scalar_one()

        assert saved_article.status == ArticleStatus.PUBLISHED.value
        assert saved_article.published_at is not None
        assert saved_article.view_count == 0

        # Verify locales
        locale_result = await db_session.execute(
            select(ArticleLocale).where(ArticleLocale.article_id == article.id)
        )
        locales = locale_result.scalars().all()
        assert len(locales) == 2

    @pytest.mark.asyncio
    async def test_article_unpublish_workflow(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test unpublishing a published article."""
        # Create and publish article
        article = Article(
            tenant_id=tenant.id,
            status=ArticleStatus.PUBLISHED.value,
            published_at=datetime.utcnow(),
        )
        db_session.add(article)
        await db_session.flush()

        locale = ArticleLocale(
            article_id=article.id,
            locale="en",
            slug="to-unpublish",
            title="Article to Unpublish",
            content="Content",
        )
        db_session.add(locale)
        await db_session.flush()

        # Unpublish
        article.unpublish()
        await db_session.flush()

        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        assert saved.status == ArticleStatus.DRAFT.value

    @pytest.mark.asyncio
    async def test_article_archive_workflow(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test archiving an article."""
        article = Article(
            tenant_id=tenant.id,
            status=ArticleStatus.PUBLISHED.value,
            published_at=datetime.utcnow(),
        )
        db_session.add(article)
        await db_session.flush()

        # Archive
        article.archive()
        await db_session.flush()

        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        assert saved.status == ArticleStatus.ARCHIVED.value

    @pytest.mark.asyncio
    async def test_article_soft_delete_workflow(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test soft deleting an article keeps data but hides it."""
        article = Article(
            tenant_id=tenant.id,
            status=ArticleStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.flush()

        article_id = article.id

        # Soft delete
        article.soft_delete()
        await db_session.flush()

        # Article should still exist
        result = await db_session.execute(
            select(Article).where(Article.id == article_id)
        )
        saved = result.scalar_one()

        assert saved.deleted_at is not None

        # But querying without soft deleted should not find it
        active_result = await db_session.execute(
            select(Article)
            .where(Article.id == article_id)
            .where(Article.deleted_at.is_(None))
        )
        active_article = active_result.scalar_one_or_none()

        assert active_article is None

    @pytest.mark.asyncio
    async def test_article_view_count_increment(
        self, db_session: AsyncSession, tenant: Tenant
    ) -> None:
        """Test incrementing view count."""
        article = Article(
            tenant_id=tenant.id,
            status=ArticleStatus.PUBLISHED.value,
            published_at=datetime.utcnow(),
            view_count=0,
        )
        db_session.add(article)
        await db_session.flush()

        # Simulate views
        for _ in range(5):
            article.view_count += 1

        await db_session.flush()

        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        saved = result.scalar_one()

        assert saved.view_count == 5

