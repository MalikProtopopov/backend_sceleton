"""Content module - article service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService, update_many_to_many
from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.core.pagination import paginate_query
from app.core.locale_helpers import (
    LocaleAlreadyExistsError,
    MinimumLocalesError,
    check_locale_exists,
    check_slug_unique,
    count_locales,
    get_locale_by_id,
    update_locale_fields,
)
from app.modules.content.models import (
    Article,
    ArticleLocale,
    ArticleStatus,
    ArticleTopic,
    Topic,
    TopicLocale,
)
from app.modules.content.schemas import (
    ArticleCreate,
    ArticleLocaleCreate,
    ArticleLocaleUpdate,
    ArticleUpdate,
)


class ArticleService(BaseService[Article]):
    """Service for managing articles."""

    model = Article

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [
            selectinload(Article.locales),
            selectinload(Article.topics).selectinload(ArticleTopic.topic),
        ]

    async def get_by_id(self, article_id: UUID, tenant_id: UUID) -> Article:
        """Get article by ID."""
        return await self._get_by_id(article_id, tenant_id)

    async def get_by_slug(self, slug: str, locale: str, tenant_id: UUID) -> Article:
        """Get published article by slug."""
        stmt = (
            select(Article)
            .join(ArticleLocale)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
            .where(Article.status == ArticleStatus.PUBLISHED.value)
            .where(ArticleLocale.locale == locale)
            .where(ArticleLocale.slug == slug)
            .options(
                selectinload(Article.locales),
                selectinload(Article.topics).selectinload(ArticleTopic.topic).selectinload(Topic.locales),
            )
        )
        result = await self.db.execute(stmt)
        article = result.scalar_one_or_none()

        if not article:
            raise NotFoundError("Article", slug)

        return article

    async def list_articles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        topic_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[Article], int]:
        """List articles with pagination and filters."""
        filters = []
        if status:
            filters.append(Article.status == status)

        base_query = self._build_base_query(tenant_id, filters=filters)

        if topic_id:
            base_query = base_query.join(ArticleTopic).where(ArticleTopic.topic_id == topic_id)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(ArticleLocale).where(
                ArticleLocale.title.ilike(search_pattern) |
                ArticleLocale.content.ilike(search_pattern) |
                ArticleLocale.slug.ilike(search_pattern)
            ).distinct()

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=[selectinload(Article.locales), selectinload(Article.topics)],
            order_by=[Article.published_at.desc().nullsfirst(), Article.created_at.desc()],
        )

    async def list_published(
        self,
        tenant_id: UUID,
        locale: str,
        page: int = 1,
        page_size: int = 20,
        topic_slug: str | None = None,
    ) -> tuple[list[Article], int]:
        """List published articles for public API."""
        # Filter by locale at database level to ensure correct pagination
        base_query = (
            select(Article)
            .join(ArticleLocale, Article.id == ArticleLocale.article_id)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
            .where(Article.status == ArticleStatus.PUBLISHED.value)
            .where(ArticleLocale.locale == locale)
        )

        if topic_slug:
            base_query = (
                base_query.join(ArticleTopic)
                .join(Topic)
                .join(TopicLocale)
                .where(TopicLocale.locale == locale)
                .where(TopicLocale.slug == topic_slug)
            )

        # Count - reflects items with requested locale
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        # Sort by sort_order first (priority), then by published_at (newest first)
        stmt = (
            base_query.options(
                selectinload(Article.locales),
                selectinload(Article.topics).selectinload(ArticleTopic.topic).selectinload(Topic.locales),
            )
            .order_by(Article.sort_order, Article.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        articles = list(result.scalars().unique().all())

        return articles, total

    @transactional
    async def create(
        self, tenant_id: UUID, data: ArticleCreate, author_id: UUID | None = None
    ) -> Article:
        """Create a new article."""
        # Check slug uniqueness
        for locale_data in data.locales:
            await check_slug_unique(
                self.db, ArticleLocale, Article, "article_id",
                locale_data.slug, locale_data.locale, tenant_id
            )

        # Create article (cover_image_url is set via separate endpoint)
        article = Article(
            tenant_id=tenant_id,
            status=data.status.value,
            reading_time_minutes=data.reading_time_minutes,
            sort_order=data.sort_order,
            author_id=author_id,
        )

        if data.status == ArticleStatus.PUBLISHED:
            article.published_at = datetime.now(UTC)

        self.db.add(article)
        await self.db.flush()

        # Create locales
        for locale_data in data.locales:
            locale = ArticleLocale(article_id=article.id, **locale_data.model_dump())
            self.db.add(locale)

        # Add topics
        for topic_id in data.topic_ids:
            at = ArticleTopic(article_id=article.id, topic_id=topic_id)
            self.db.add(at)

        await self.db.flush()
        await self.db.refresh(article)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(article, ["locales", "topics"])  # Eager load relationships

        return article

    @transactional
    async def update(self, article_id: UUID, tenant_id: UUID, data: ArticleUpdate) -> Article:
        """Update an article."""
        article = await self.get_by_id(article_id, tenant_id)
        article.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version", "topic_ids"})

        # Handle status change to published
        if "status" in update_data:
            new_status = update_data["status"]
            if isinstance(new_status, ArticleStatus):
                update_data["status"] = new_status.value
            if new_status == ArticleStatus.PUBLISHED and article.status != ArticleStatus.PUBLISHED.value:
                article.published_at = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(article, field, value)

        # Update topics if provided
        if data.topic_ids is not None:
            await update_many_to_many(
                self.db,
                article,
                "topics",
                data.topic_ids,
                ArticleTopic,
                "article_id",
                "topic_id",
            )

        await self.db.flush()
        await self.db.refresh(article)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(article, ["locales", "topics"])  # Eager load relationships

        return article

    @transactional
    async def publish(self, article_id: UUID, tenant_id: UUID) -> Article:
        """Publish an article."""
        article = await self.get_by_id(article_id, tenant_id)
        article.publish()
        await self.db.flush()
        await self.db.refresh(article)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(article, ["locales", "topics"])  # Eager load relationships
        return article

    @transactional
    async def unpublish(self, article_id: UUID, tenant_id: UUID) -> Article:
        """Unpublish an article (move to draft)."""
        article = await self.get_by_id(article_id, tenant_id)
        article.unpublish()
        await self.db.flush()
        await self.db.refresh(article)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(article, ["locales", "topics"])  # Eager load relationships
        return article

    @transactional
    async def soft_delete(self, article_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an article."""
        await self._soft_delete(article_id, tenant_id)

    @transactional
    async def increment_view(self, article_id: UUID, tenant_id: UUID) -> None:
        """Increment article view count."""
        article = await self.get_by_id(article_id, tenant_id)
        article.view_count += 1
        await self.db.flush()

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, article_id: UUID, tenant_id: UUID, data: ArticleLocaleCreate
    ) -> ArticleLocale:
        """Create a new locale for an article."""
        # Verify article exists
        await self.get_by_id(article_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, ArticleLocale, "article_id", article_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Article", data.locale)

        # Check slug uniqueness
        await check_slug_unique(
            self.db, ArticleLocale, Article, "article_id",
            data.slug, data.locale, tenant_id
        )

        locale = ArticleLocale(
            article_id=article_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, article_id: UUID, tenant_id: UUID, data: ArticleLocaleUpdate
    ) -> ArticleLocale:
        """Update an article locale."""
        # Verify article exists
        await self.get_by_id(article_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, ArticleLocale, locale_id, "article_id", article_id, "Article"
        )

        # Check slug uniqueness if slug is being updated
        if data.slug and data.slug != locale.slug:
            await check_slug_unique(
                self.db, ArticleLocale, Article, "article_id",
                data.slug, locale.locale, tenant_id, exclude_locale_id=locale_id
            )

        # Update fields
        update_locale_fields(
            locale, data,
            ["title", "slug", "excerpt", "content", "meta_title", "meta_description"]
        )

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_cover_image_url(
        self, article_id: UUID, tenant_id: UUID, url: str | None
    ) -> Article:
        """Update or clear the article cover image URL."""
        article = await self.get_by_id(article_id, tenant_id)
        article.cover_image_url = url
        await self.db.flush()
        await self.db.refresh(article)
        await self.db.refresh(article, ["locales", "topics"])
        return article

    @transactional
    async def delete_locale(self, locale_id: UUID, article_id: UUID, tenant_id: UUID) -> None:
        """Delete an article locale."""
        # Verify article exists
        await self.get_by_id(article_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, ArticleLocale, "article_id", article_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Article")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, ArticleLocale, locale_id, "article_id", article_id, "Article"
        )
        await self.db.delete(locale)
        await self.db.flush()
