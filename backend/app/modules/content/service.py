"""Content module service layer."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import NotFoundError, VersionConflictError
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
    Case,
    CaseLocale,
    CaseServiceLink,
    FAQ,
    FAQLocale,
    Review,
    ReviewStatus,
    Topic,
    TopicLocale,
)
from app.modules.content.schemas import (
    ArticleCreate,
    ArticleLocaleCreate,
    ArticleLocaleUpdate,
    ArticleUpdate,
    BulkAction,
    BulkOperationItemResult,
    BulkOperationRequest,
    BulkOperationSummary,
    BulkResourceType,
    CaseCreate,
    CaseLocaleCreate,
    CaseLocaleUpdate,
    CaseUpdate,
    FAQCreate,
    FAQLocaleCreate,
    FAQLocaleUpdate,
    FAQUpdate,
    ReviewCreate,
    ReviewUpdate,
    TopicCreate,
    TopicLocaleCreate,
    TopicLocaleUpdate,
    TopicUpdate,
)


class TopicService:
    """Service for managing topics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, topic_id: UUID, tenant_id: UUID) -> Topic:
        """Get topic by ID."""
        stmt = (
            select(Topic)
            .where(Topic.id == topic_id)
            .where(Topic.tenant_id == tenant_id)
            .where(Topic.deleted_at.is_(None))
            .options(selectinload(Topic.locales))
        )
        result = await self.db.execute(stmt)
        topic = result.scalar_one_or_none()

        if not topic:
            raise NotFoundError("Topic", topic_id)

        return topic

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
        await self.db.refresh(topic, ["locales"])

        return topic

    @transactional
    async def update(self, topic_id: UUID, tenant_id: UUID, data: TopicUpdate) -> Topic:
        """Update a topic."""
        topic = await self.get_by_id(topic_id, tenant_id)

        if topic.version != data.version:
            raise VersionConflictError("Topic", topic.version, data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(topic, field, value)

        await self.db.flush()
        await self.db.refresh(topic, ["locales"])

        return topic

    @transactional
    async def soft_delete(self, topic_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a topic."""
        topic = await self.get_by_id(topic_id, tenant_id)
        topic.soft_delete()
        await self.db.flush()

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


class ArticleService:
    """Service for managing articles."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, article_id: UUID, tenant_id: UUID) -> Article:
        """Get article by ID."""
        stmt = (
            select(Article)
            .where(Article.id == article_id)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
            .options(
                selectinload(Article.locales),
                selectinload(Article.topics).selectinload(ArticleTopic.topic),
            )
        )
        result = await self.db.execute(stmt)
        article = result.scalar_one_or_none()

        if not article:
            raise NotFoundError("Article", article_id)

        return article

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
        base_query = (
            select(Article)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
        )

        if status:
            base_query = base_query.where(Article.status == status)

        if topic_id:
            base_query = base_query.join(ArticleTopic).where(ArticleTopic.topic_id == topic_id)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(ArticleLocale).where(
                ArticleLocale.title.ilike(search_pattern) |
                ArticleLocale.content.ilike(search_pattern) |
                ArticleLocale.slug.ilike(search_pattern)
            ).distinct()

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(selectinload(Article.locales), selectinload(Article.topics))
            .order_by(Article.published_at.desc().nullsfirst(), Article.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        articles = list(result.scalars().all())

        return articles, total

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
        stmt = (
            base_query.options(
                selectinload(Article.locales),
                selectinload(Article.topics).selectinload(ArticleTopic.topic).selectinload(Topic.locales),
            )
            .order_by(Article.published_at.desc())
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
            article.published_at = datetime.utcnow()

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
        await self.db.refresh(article, ["locales", "topics"])

        return article

    @transactional
    async def update(self, article_id: UUID, tenant_id: UUID, data: ArticleUpdate) -> Article:
        """Update an article."""
        article = await self.get_by_id(article_id, tenant_id)

        if article.version != data.version:
            raise VersionConflictError("Article", article.version, data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version", "topic_ids"})

        # Handle status change to published
        if "status" in update_data:
            new_status = update_data["status"]
            if isinstance(new_status, ArticleStatus):
                update_data["status"] = new_status.value
            if new_status == ArticleStatus.PUBLISHED and article.status != ArticleStatus.PUBLISHED.value:
                article.published_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(article, field, value)

        # Update topics if provided
        if data.topic_ids is not None:
            # Remove existing
            for at in article.topics:
                await self.db.delete(at)

            # Add new
            for topic_id in data.topic_ids:
                at = ArticleTopic(article_id=article.id, topic_id=topic_id)
                self.db.add(at)

        await self.db.flush()
        await self.db.refresh(article, ["locales", "topics"])

        return article

    @transactional
    async def publish(self, article_id: UUID, tenant_id: UUID) -> Article:
        """Publish an article."""
        article = await self.get_by_id(article_id, tenant_id)
        article.publish()
        await self.db.flush()
        return article

    @transactional
    async def unpublish(self, article_id: UUID, tenant_id: UUID) -> Article:
        """Unpublish an article (move to draft)."""
        article = await self.get_by_id(article_id, tenant_id)
        article.unpublish()
        await self.db.flush()
        return article

    @transactional
    async def soft_delete(self, article_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an article."""
        article = await self.get_by_id(article_id, tenant_id)
        article.soft_delete()
        await self.db.flush()

    async def increment_view(self, article_id: UUID, tenant_id: UUID) -> None:
        """Increment article view count."""
        article = await self.get_by_id(article_id, tenant_id)
        article.view_count += 1
        await self.db.commit()

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


class FAQService:
    """Service for managing FAQ."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, faq_id: UUID, tenant_id: UUID) -> FAQ:
        """Get FAQ by ID."""
        stmt = (
            select(FAQ)
            .where(FAQ.id == faq_id)
            .where(FAQ.tenant_id == tenant_id)
            .where(FAQ.deleted_at.is_(None))
            .options(selectinload(FAQ.locales))
        )
        result = await self.db.execute(stmt)
        faq = result.scalar_one_or_none()

        if not faq:
            raise NotFoundError("FAQ", faq_id)

        return faq

    async def list_faqs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        category: str | None = None,
        is_published: bool | None = None,
    ) -> tuple[list[FAQ], int]:
        """List FAQs with pagination."""
        base_query = (
            select(FAQ)
            .where(FAQ.tenant_id == tenant_id)
            .where(FAQ.deleted_at.is_(None))
        )

        if category:
            base_query = base_query.where(FAQ.category == category)

        if is_published is not None:
            base_query = base_query.where(FAQ.is_published == is_published)

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(selectinload(FAQ.locales))
            .order_by(FAQ.category.nullsfirst(), FAQ.sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        faqs = list(result.scalars().all())

        return faqs, total

    async def list_published(
        self, tenant_id: UUID, locale: str, category: str | None = None
    ) -> list[FAQ]:
        """List published FAQs for public API."""
        # Filter by locale at database level to ensure only FAQs with the locale are returned
        stmt = (
            select(FAQ)
            .join(FAQLocale, FAQ.id == FAQLocale.faq_id)
            .where(FAQ.tenant_id == tenant_id)
            .where(FAQ.deleted_at.is_(None))
            .where(FAQ.is_published.is_(True))
            .where(FAQLocale.locale == locale)
            .options(selectinload(FAQ.locales))
            .order_by(FAQ.category.nullsfirst(), FAQ.sort_order)
        )

        if category:
            stmt = stmt.where(FAQ.category == category)

        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    @transactional
    async def create(self, tenant_id: UUID, data: FAQCreate) -> FAQ:
        """Create a new FAQ."""
        faq = FAQ(
            tenant_id=tenant_id,
            category=data.category,
            is_published=data.is_published,
            sort_order=data.sort_order,
        )
        self.db.add(faq)
        await self.db.flush()

        for locale_data in data.locales:
            locale = FAQLocale(faq_id=faq.id, **locale_data.model_dump())
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(faq, ["locales"])

        return faq

    @transactional
    async def update(self, faq_id: UUID, tenant_id: UUID, data: FAQUpdate) -> FAQ:
        """Update a FAQ."""
        faq = await self.get_by_id(faq_id, tenant_id)

        if faq.version != data.version:
            raise VersionConflictError("FAQ", faq.version, data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(faq, field, value)

        await self.db.flush()
        await self.db.refresh(faq, ["locales"])

        return faq

    @transactional
    async def soft_delete(self, faq_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a FAQ."""
        faq = await self.get_by_id(faq_id, tenant_id)
        faq.soft_delete()
        await self.db.flush()

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, faq_id: UUID, tenant_id: UUID, data: FAQLocaleCreate
    ) -> FAQLocale:
        """Create a new locale for a FAQ."""
        # Verify FAQ exists
        await self.get_by_id(faq_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, FAQLocale, "faq_id", faq_id, data.locale
        ):
            raise LocaleAlreadyExistsError("FAQ", data.locale)

        locale = FAQLocale(
            faq_id=faq_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, faq_id: UUID, tenant_id: UUID, data: FAQLocaleUpdate
    ) -> FAQLocale:
        """Update a FAQ locale."""
        # Verify FAQ exists
        await self.get_by_id(faq_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, FAQLocale, locale_id, "faq_id", faq_id, "FAQ"
        )

        # Update fields
        update_locale_fields(locale, data, ["question", "answer"])

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, faq_id: UUID, tenant_id: UUID) -> None:
        """Delete a FAQ locale."""
        # Verify FAQ exists
        await self.get_by_id(faq_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, FAQLocale, "faq_id", faq_id)
        if locale_count <= 1:
            raise MinimumLocalesError("FAQ")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, FAQLocale, locale_id, "faq_id", faq_id, "FAQ"
        )
        await self.db.delete(locale)
        await self.db.flush()


class CaseService:
    """Service for managing cases (portfolio / case studies)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, case_id: UUID, tenant_id: UUID) -> Case:
        """Get case by ID."""
        stmt = (
            select(Case)
            .where(Case.id == case_id)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .options(
                selectinload(Case.locales),
                selectinload(Case.services),
            )
        )
        result = await self.db.execute(stmt)
        case = result.scalar_one_or_none()

        if not case:
            raise NotFoundError("Case", case_id)

        return case

    async def get_by_slug(self, slug: str, locale: str, tenant_id: UUID) -> Case:
        """Get published case by slug."""
        stmt = (
            select(Case)
            .join(CaseLocale)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == ArticleStatus.PUBLISHED.value)
            .where(CaseLocale.locale == locale)
            .where(CaseLocale.slug == slug)
            .options(
                selectinload(Case.locales),
                selectinload(Case.services),
            )
        )
        result = await self.db.execute(stmt)
        case = result.scalar_one_or_none()

        if not case:
            raise NotFoundError("Case", slug)

        return case

    async def list_cases(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        is_featured: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Case], int]:
        """List cases with pagination and filters."""
        base_query = (
            select(Case)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
        )

        if status:
            base_query = base_query.where(Case.status == status)

        if is_featured is not None:
            base_query = base_query.where(Case.is_featured == is_featured)

        if search:
            # Search in client_name and locales title
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(CaseLocale).where(
                (Case.client_name.ilike(search_pattern)) |
                (CaseLocale.title.ilike(search_pattern))
            ).distinct()

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(selectinload(Case.locales), selectinload(Case.services))
            .order_by(Case.published_at.desc().nullsfirst(), Case.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        cases = list(result.scalars().unique().all())

        return cases, total

    async def list_published(
        self,
        tenant_id: UUID,
        locale: str,
        page: int = 1,
        page_size: int = 20,
        is_featured: bool | None = None,
    ) -> tuple[list[Case], int]:
        """List published cases for public API."""
        # Filter by locale at database level to ensure correct pagination
        base_query = (
            select(Case)
            .join(CaseLocale, Case.id == CaseLocale.case_id)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == ArticleStatus.PUBLISHED.value)
            .where(CaseLocale.locale == locale)
        )

        if is_featured is not None:
            base_query = base_query.where(Case.is_featured == is_featured)

        # Count - reflects items with requested locale
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(
                selectinload(Case.locales),
                selectinload(Case.services),
            )
            .order_by(Case.sort_order, Case.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        cases = list(result.scalars().unique().all())

        return cases, total

    @transactional
    async def create(self, tenant_id: UUID, data: CaseCreate) -> Case:
        """Create a new case."""
        # Check slug uniqueness
        for locale_data in data.locales:
            await check_slug_unique(
                self.db, CaseLocale, Case, "case_id",
                locale_data.slug, locale_data.locale, tenant_id
            )

        # Create case (cover_image_url is set via separate endpoint)
        case = Case(
            tenant_id=tenant_id,
            status=data.status.value,
            client_name=data.client_name,
            project_year=data.project_year,
            project_duration=data.project_duration,
            is_featured=data.is_featured,
            sort_order=data.sort_order,
        )

        if data.status.value == ArticleStatus.PUBLISHED.value:
            case.published_at = datetime.utcnow()

        self.db.add(case)
        await self.db.flush()

        # Create locales
        for locale_data in data.locales:
            locale = CaseLocale(case_id=case.id, **locale_data.model_dump())
            self.db.add(locale)

        # Add service links
        for service_id in data.service_ids:
            link = CaseServiceLink(case_id=case.id, service_id=service_id)
            self.db.add(link)

        await self.db.flush()
        await self.db.refresh(case, ["locales", "services"])

        return case

    @transactional
    async def update(self, case_id: UUID, tenant_id: UUID, data: CaseUpdate) -> Case:
        """Update a case."""
        case = await self.get_by_id(case_id, tenant_id)

        if case.version != data.version:
            raise VersionConflictError("Case", case.version, data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version", "service_ids"})

        # Handle status change to published
        if "status" in update_data:
            new_status = update_data["status"]
            if hasattr(new_status, "value"):
                update_data["status"] = new_status.value
            if new_status == ArticleStatus.PUBLISHED and case.status != ArticleStatus.PUBLISHED.value:
                case.published_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(case, field, value)

        # Update service links if provided
        if data.service_ids is not None:
            # Remove existing
            for link in case.services:
                await self.db.delete(link)

            # Add new
            for service_id in data.service_ids:
                link = CaseServiceLink(case_id=case.id, service_id=service_id)
                self.db.add(link)

        await self.db.flush()
        await self.db.refresh(case, ["locales", "services"])

        return case

    @transactional
    async def publish(self, case_id: UUID, tenant_id: UUID) -> Case:
        """Publish a case."""
        case = await self.get_by_id(case_id, tenant_id)
        case.status = ArticleStatus.PUBLISHED.value
        if not case.published_at:
            case.published_at = datetime.utcnow()
        await self.db.flush()
        return case

    @transactional
    async def unpublish(self, case_id: UUID, tenant_id: UUID) -> Case:
        """Unpublish a case (move to draft)."""
        case = await self.get_by_id(case_id, tenant_id)
        case.status = ArticleStatus.DRAFT.value
        await self.db.flush()
        return case

    @transactional
    async def soft_delete(self, case_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a case."""
        case = await self.get_by_id(case_id, tenant_id)
        case.soft_delete()
        await self.db.flush()

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, case_id: UUID, tenant_id: UUID, data: CaseLocaleCreate
    ) -> CaseLocale:
        """Create a new locale for a case."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, CaseLocale, "case_id", case_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Case", data.locale)

        # Check slug uniqueness
        await check_slug_unique(
            self.db, CaseLocale, Case, "case_id",
            data.slug, data.locale, tenant_id
        )

        locale = CaseLocale(
            case_id=case_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, case_id: UUID, tenant_id: UUID, data: CaseLocaleUpdate
    ) -> CaseLocale:
        """Update a case locale."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, CaseLocale, locale_id, "case_id", case_id, "Case"
        )

        # Check slug uniqueness if slug is being updated
        if data.slug and data.slug != locale.slug:
            await check_slug_unique(
                self.db, CaseLocale, Case, "case_id",
                data.slug, locale.locale, tenant_id, exclude_locale_id=locale_id
            )

        # Update fields
        update_locale_fields(
            locale, data,
            ["title", "slug", "excerpt", "description", "results", "meta_title", "meta_description"]
        )

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, case_id: UUID, tenant_id: UUID) -> None:
        """Delete a case locale."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, CaseLocale, "case_id", case_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Case")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, CaseLocale, locale_id, "case_id", case_id, "Case"
        )
        await self.db.delete(locale)
        await self.db.flush()


class ReviewService:
    """Service for managing reviews."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, review_id: UUID, tenant_id: UUID) -> Review:
        """Get review by ID."""
        stmt = (
            select(Review)
            .where(Review.id == review_id)
            .where(Review.tenant_id == tenant_id)
            .where(Review.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        review = result.scalar_one_or_none()

        if not review:
            raise NotFoundError("Review", review_id)

        return review

    async def list_reviews(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        case_id: UUID | None = None,
        is_featured: bool | None = None,
    ) -> tuple[list[Review], int]:
        """List reviews with pagination and filters."""
        base_query = (
            select(Review)
            .where(Review.tenant_id == tenant_id)
            .where(Review.deleted_at.is_(None))
        )

        if status:
            base_query = base_query.where(Review.status == status)

        if case_id:
            base_query = base_query.where(Review.case_id == case_id)

        if is_featured is not None:
            base_query = base_query.where(Review.is_featured == is_featured)

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query
            .order_by(Review.sort_order, Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        reviews = list(result.scalars().all())

        return reviews, total

    async def list_approved(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        case_id: UUID | None = None,
        is_featured: bool | None = None,
    ) -> tuple[list[Review], int]:
        """List approved reviews for public API."""
        base_query = (
            select(Review)
            .where(Review.tenant_id == tenant_id)
            .where(Review.deleted_at.is_(None))
            .where(Review.status == ReviewStatus.APPROVED.value)
        )

        if case_id:
            base_query = base_query.where(Review.case_id == case_id)

        if is_featured is not None:
            base_query = base_query.where(Review.is_featured == is_featured)

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query
            .order_by(Review.sort_order, Review.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        reviews = list(result.scalars().all())

        return reviews, total

    @transactional
    async def create(self, tenant_id: UUID, data: ReviewCreate) -> Review:
        """Create a new review."""
        # author_photo_url is set via separate endpoint
        review = Review(
            tenant_id=tenant_id,
            rating=data.rating,
            author_name=data.author_name,
            author_company=data.author_company,
            author_position=data.author_position,
            content=data.content,
            case_id=data.case_id,
            is_featured=data.is_featured,
            source=data.source,
            source_url=data.source_url,
            review_date=data.review_date,
            sort_order=data.sort_order,
            status=ReviewStatus.PENDING.value,
        )
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)

        return review

    @transactional
    async def update(self, review_id: UUID, tenant_id: UUID, data: ReviewUpdate) -> Review:
        """Update a review."""
        review = await self.get_by_id(review_id, tenant_id)

        if review.version != data.version:
            raise VersionConflictError("Review", review.version, data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        # Handle status enum
        if "status" in update_data:
            status_val = update_data["status"]
            if hasattr(status_val, "value"):
                update_data["status"] = status_val.value

        for field, value in update_data.items():
            setattr(review, field, value)

        await self.db.flush()
        await self.db.refresh(review)

        return review

    @transactional
    async def approve(self, review_id: UUID, tenant_id: UUID) -> Review:
        """Approve a review."""
        review = await self.get_by_id(review_id, tenant_id)
        review.approve()
        await self.db.flush()
        return review

    @transactional
    async def reject(self, review_id: UUID, tenant_id: UUID) -> Review:
        """Reject a review."""
        review = await self.get_by_id(review_id, tenant_id)
        review.reject()
        await self.db.flush()
        return review

    @transactional
    async def soft_delete(self, review_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a review."""
        review = await self.get_by_id(review_id, tenant_id)
        review.soft_delete()
        await self.db.flush()


class BulkOperationService:
    """Service for bulk operations on content."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.article_service = ArticleService(db)
        self.case_service = CaseService(db)
        self.faq_service = FAQService(db)
        self.review_service = ReviewService(db)

    async def execute(
        self, tenant_id: UUID, request: BulkOperationRequest
    ) -> BulkOperationSummary:
        """Execute bulk operation synchronously."""
        results: list[BulkOperationItemResult] = []

        for item_id in request.ids:
            try:
                await self._execute_single(
                    tenant_id=tenant_id,
                    resource_type=request.resource_type,
                    action=request.action,
                    item_id=item_id,
                )
                results.append(BulkOperationItemResult(
                    id=item_id,
                    status="success",
                    message=f"{request.action.value} completed",
                ))
            except Exception as e:
                results.append(BulkOperationItemResult(
                    id=item_id,
                    status="error",
                    message=str(e),
                ))

        succeeded = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "error")

        return BulkOperationSummary(
            total=len(request.ids),
            succeeded=succeeded,
            failed=failed,
            details=results,
        )

    async def _execute_single(
        self,
        tenant_id: UUID,
        resource_type: BulkResourceType,
        action: BulkAction,
        item_id: UUID,
    ) -> None:
        """Execute action on a single resource."""
        if resource_type == BulkResourceType.ARTICLES:
            await self._execute_article_action(tenant_id, action, item_id)
        elif resource_type == BulkResourceType.CASES:
            await self._execute_case_action(tenant_id, action, item_id)
        elif resource_type == BulkResourceType.FAQ:
            await self._execute_faq_action(tenant_id, action, item_id)
        elif resource_type == BulkResourceType.REVIEWS:
            await self._execute_review_action(tenant_id, action, item_id)

    async def _execute_article_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on an article."""
        if action == BulkAction.PUBLISH:
            await self.article_service.publish(item_id, tenant_id)
        elif action == BulkAction.UNPUBLISH:
            await self.article_service.unpublish(item_id, tenant_id)
        elif action == BulkAction.ARCHIVE:
            article = await self.article_service.get_by_id(item_id, tenant_id)
            article.archive()
            await self.db.commit()
        elif action == BulkAction.DELETE:
            await self.article_service.soft_delete(item_id, tenant_id)

    async def _execute_case_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on a case."""
        if action == BulkAction.PUBLISH:
            await self.case_service.publish(item_id, tenant_id)
        elif action == BulkAction.UNPUBLISH:
            await self.case_service.unpublish(item_id, tenant_id)
        elif action == BulkAction.ARCHIVE:
            case = await self.case_service.get_by_id(item_id, tenant_id)
            case.status = ArticleStatus.ARCHIVED.value
            await self.db.commit()
        elif action == BulkAction.DELETE:
            await self.case_service.soft_delete(item_id, tenant_id)

    async def _execute_faq_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on a FAQ."""
        faq = await self.faq_service.get_by_id(item_id, tenant_id)
        if action == BulkAction.PUBLISH:
            faq.is_published = True
            await self.db.commit()
        elif action == BulkAction.UNPUBLISH:
            faq.is_published = False
            await self.db.commit()
        elif action == BulkAction.DELETE:
            await self.faq_service.soft_delete(item_id, tenant_id)
        # Archive not applicable for FAQ

    async def _execute_review_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on a review."""
        if action == BulkAction.PUBLISH:
            # For reviews, publish means approve
            await self.review_service.approve(item_id, tenant_id)
        elif action == BulkAction.UNPUBLISH:
            # For reviews, unpublish means reject
            await self.review_service.reject(item_id, tenant_id)
        elif action == BulkAction.DELETE:
            await self.review_service.soft_delete(item_id, tenant_id)
        # Archive not applicable for reviews

