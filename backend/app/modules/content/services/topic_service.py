"""Content module - topic service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.modules.localization.helpers import (
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
    ArticleStatus,
    ArticleTopic,
    Topic,
    TopicLocale,
)
from app.modules.content.schemas import (
    TopicCreate,
    TopicLocaleCreate,
    TopicLocaleUpdate,
    TopicUpdate,
)


class TopicService(BaseService[Topic]):
    """Service for managing topics."""

    model = Topic

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(Topic.locales)]

    async def get_by_id(self, topic_id: UUID, tenant_id: UUID) -> Topic:
        """Get topic by ID."""
        return await self._get_by_id(topic_id, tenant_id)

    async def list_topics(self, tenant_id: UUID, locale: str | None = None) -> list[Topic]:
        """List all topics for a tenant.
        
        If locale is provided, filters to only topics that have that locale.
        """
        if locale:
            # Filter by locale at database level
            stmt = (
                select(Topic)
                .join(TopicLocale, Topic.id == TopicLocale.topic_id)
                .where(Topic.tenant_id == tenant_id)
                .where(Topic.deleted_at.is_(None))
                .where(TopicLocale.locale == locale)
                .options(selectinload(Topic.locales))
                .order_by(Topic.sort_order)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().unique().all())
        else:
            # Return all topics (admin use case)
            stmt = (
                select(Topic)
                .where(Topic.tenant_id == tenant_id)
                .where(Topic.deleted_at.is_(None))
                .options(selectinload(Topic.locales))
                .order_by(Topic.sort_order)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())

    async def list_topics_with_article_count(
        self, tenant_id: UUID, locale: str, only_with_articles: bool = False
    ) -> list[tuple[Topic, int]]:
        """List topics with article count for public API.
        
        Args:
            tenant_id: Tenant ID
            locale: Locale code
            only_with_articles: If True, only return topics that have published articles
            
        Returns:
            List of tuples (Topic, article_count)
        """
        from app.modules.content.models import Article, ArticleTopic, ArticleLocale
        
        # Base query: topics with locale
        base_query = (
            select(
                Topic,
                func.count(Article.id.distinct()).label('article_count')
            )
            .join(TopicLocale, Topic.id == TopicLocale.topic_id)
            .outerjoin(
                ArticleTopic,
                Topic.id == ArticleTopic.topic_id
            )
            .outerjoin(
                Article,
                (ArticleTopic.article_id == Article.id)
                & (Article.tenant_id == tenant_id)
                & (Article.deleted_at.is_(None))
                & (Article.status == ArticleStatus.PUBLISHED.value)
            )
            .outerjoin(
                ArticleLocale,
                (Article.id == ArticleLocale.article_id)
                & (ArticleLocale.locale == locale)
            )
            .where(Topic.tenant_id == tenant_id)
            .where(Topic.deleted_at.is_(None))
            .where(TopicLocale.locale == locale)
            .group_by(Topic.id, TopicLocale.id)
            .order_by(Topic.sort_order)
        )
        
        result = await self.db.execute(base_query)
        rows = result.all()
        
        # Extract topics and counts from rows
        topics_with_counts = []
        for row in rows:
            topic = row[0]
            count = int(row[1]) if row[1] is not None else 0
            topics_with_counts.append((topic, count))
        
        # Filter by article count if needed
        if only_with_articles:
            topics_with_counts = [
                (topic, count) for topic, count in topics_with_counts if count > 0
            ]
        
        return topics_with_counts

    async def get_by_slug(self, slug: str, locale: str, tenant_id: UUID) -> Topic:
        """Get topic by slug and locale.
        
        Note: If multiple topics have the same slug, returns the first one found.
        """
        # First find TopicLocale, then load Topic to avoid JOIN duplicates
        stmt = (
            select(TopicLocale)
            .join(Topic)
            .where(Topic.tenant_id == tenant_id)
            .where(Topic.deleted_at.is_(None))
            .where(TopicLocale.locale == locale)
            .where(TopicLocale.slug == slug)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        topic_locale = result.scalar_one_or_none()

        if not topic_locale:
            raise NotFoundError("Topic", slug)

        # Load topic with locales
        topic = await self.get_by_id(topic_locale.topic_id, tenant_id)
        return topic

    async def count_articles(self, topic_id: UUID) -> int:
        """Count published articles for a topic."""
        stmt = (
            select(func.count(ArticleTopic.article_id))
            .join(Article)
            .where(ArticleTopic.topic_id == topic_id)
            .where(Article.deleted_at.is_(None))
            .where(Article.status == ArticleStatus.PUBLISHED)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    @transactional
    async def create(self, tenant_id: UUID, data: TopicCreate) -> Topic:
        """Create a new topic."""
        topic = Topic(
            tenant_id=tenant_id,
            icon=data.icon,
            color=data.color,
            sort_order=data.sort_order,
        )
        self.db.add(topic)
        await self.db.flush()

        for locale_data in data.locales:
            locale = TopicLocale(topic_id=topic.id, **locale_data.model_dump())
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(topic)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(topic, ["locales"])

        return topic

    @transactional
    async def update(self, topic_id: UUID, tenant_id: UUID, data: TopicUpdate) -> Topic:
        """Update a topic."""
        topic = await self.get_by_id(topic_id, tenant_id)
        topic.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(topic, field, value)

        await self.db.flush()
        await self.db.refresh(topic)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(topic, ["locales"])

        return topic

    @transactional
    async def soft_delete(self, topic_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a topic."""
        await self._soft_delete(topic_id, tenant_id)

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, topic_id: UUID, tenant_id: UUID, data: TopicLocaleCreate
    ) -> TopicLocale:
        """Create a new locale for a topic."""
        # Verify topic exists
        await self.get_by_id(topic_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, TopicLocale, "topic_id", topic_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Topic", data.locale)

        # Check slug uniqueness
        await check_slug_unique(
            self.db, TopicLocale, Topic, "topic_id",
            data.slug, data.locale, tenant_id
        )

        locale = TopicLocale(
            topic_id=topic_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, topic_id: UUID, tenant_id: UUID, data: TopicLocaleUpdate
    ) -> TopicLocale:
        """Update a topic locale."""
        # Verify topic exists
        await self.get_by_id(topic_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, TopicLocale, locale_id, "topic_id", topic_id, "Topic"
        )

        # Check slug uniqueness if slug is being updated
        if data.slug and data.slug != locale.slug:
            await check_slug_unique(
                self.db, TopicLocale, Topic, "topic_id",
                data.slug, locale.locale, tenant_id, exclude_locale_id=locale_id
            )

        # Update fields
        update_locale_fields(
            locale, data,
            ["title", "slug", "description", "meta_title", "meta_description"]
        )

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, topic_id: UUID, tenant_id: UUID) -> None:
        """Delete a topic locale."""
        # Verify topic exists
        await self.get_by_id(topic_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, TopicLocale, "topic_id", topic_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Topic")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, TopicLocale, locale_id, "topic_id", topic_id, "Topic"
        )
        await self.db.delete(locale)
        await self.db.flush()
