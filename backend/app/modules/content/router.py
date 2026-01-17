"""API routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Filtering, Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_active_user, get_current_tenant_id
from app.modules.auth.models import AdminUser
from app.modules.content.schemas import (
    ArticleCreate,
    ArticleListResponse,
    ArticleLocaleCreate,
    ArticleLocaleResponse,
    ArticleLocaleUpdate,
    ArticlePublicListResponse,
    ArticlePublicResponse,
    ArticleResponse,
    ArticleUpdate,
    BulkOperationRequest,
    BulkOperationResponse,
    CaseCreate,
    CaseListResponse,
    CaseLocaleCreate,
    CaseLocaleResponse,
    CaseLocaleUpdate,
    CasePublicListResponse,
    CasePublicResponse,
    CaseResponse,
    CaseUpdate,
    FAQCreate,
    FAQListResponse,
    FAQLocaleCreate,
    FAQLocaleResponse,
    FAQLocaleUpdate,
    FAQPublicResponse,
    FAQResponse,
    FAQUpdate,
    ReviewCreate,
    ReviewListResponse,
    ReviewPublicListResponse,
    ReviewPublicResponse,
    ReviewResponse,
    ReviewUpdate,
    TopicCreate,
    TopicDetailPublicResponse,
    TopicLocaleCreate,
    TopicPublicResponse,
    TopicWithArticlesCountPublicResponse,
    TopicLocaleResponse,
    TopicLocaleUpdate,
    TopicPublicResponse,
    TopicResponse,
    TopicUpdate,
)
from app.modules.content.mappers import (
    map_article_to_public_response,
    map_articles_to_public_response,
    map_case_to_public_response,
    map_cases_to_public_response,
    map_faqs_to_public_response,
    map_topic_to_detail_public_response,
    map_topics_with_counts_to_public_response,
)
from app.modules.content.service import (
    ArticleService,
    BulkOperationService,
    CaseService,
    FAQService,
    ReviewService,
    TopicService,
)

router = APIRouter()


# ============================================================================
# Public Routes - Articles
# ============================================================================


@router.get(
    "/public/articles",
    response_model=ArticlePublicListResponse,
    summary="List published articles",
    tags=["Public - Content"],
)
async def list_articles_public(
    locale: Locale,
    pagination: Pagination,
    tenant_id: PublicTenantId,
    topic: str | None = Query(default=None, description="Filter by topic slug"),
    db: AsyncSession = Depends(get_db),
) -> ArticlePublicListResponse:
    """List published articles for public display."""
    service = ArticleService(db)
    articles, total = await service.list_published(
        tenant_id=tenant_id,
        locale=locale.locale,
        page=pagination.page,
        page_size=pagination.page_size,
        topic_slug=topic,
    )

    items = map_articles_to_public_response(articles, locale.locale, include_content=False)

    return ArticlePublicListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/public/articles/{slug}",
    response_model=ArticlePublicResponse,
    summary="Get article by slug",
    tags=["Public - Content"],
)
async def get_article_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> ArticlePublicResponse:
    """Get a published article by slug."""
    service = ArticleService(db)
    article = await service.get_by_slug(slug, locale.locale, tenant_id)

    # Increment view count (fire and forget)
    await service.increment_view(article.id, tenant_id)

    return map_article_to_public_response(article, locale.locale, include_content=True)


@router.get(
    "/public/topics",
    response_model=list[TopicWithArticlesCountPublicResponse],
    summary="List topics with article count",
    tags=["Public - Content"],
)
async def list_topics_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    only_with_articles: bool = Query(
        default=False,
        description="If true, only return topics that have published articles"
    ),
    db: AsyncSession = Depends(get_db),
) -> list[TopicWithArticlesCountPublicResponse]:
    """List all topics with article count.
    
    Returns all topics for the given locale, optionally filtered to only
    topics that have published articles. Each topic includes the count
    of published articles.
    """
    service = TopicService(db)
    topics_with_counts = await service.list_topics_with_article_count(
        tenant_id, locale.locale, only_with_articles=only_with_articles
    )

    return map_topics_with_counts_to_public_response(topics_with_counts, locale.locale)


@router.get(
    "/public/topics/{slug}",
    response_model=TopicDetailPublicResponse,
    summary="Get topic by slug",
    tags=["Public - Content"],
)
async def get_topic_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> TopicDetailPublicResponse:
    """Get topic details by slug for SEO and topic page.
    
    Returns topic with SEO fields and article count.
    """
    service = TopicService(db)
    topic = await service.get_by_slug(slug, locale.locale, tenant_id)

    # Count articles for this topic
    articles_count = await service.count_articles(topic.id)

    return map_topic_to_detail_public_response(topic, locale.locale, articles_count)


@router.get(
    "/public/faq",
    response_model=list[FAQPublicResponse],
    summary="List FAQ",
    tags=["Public - Content"],
)
async def list_faq_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    category: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[FAQPublicResponse]:
    """List published FAQ items."""
    service = FAQService(db)
    faqs = await service.list_published(tenant_id, locale.locale, category)
    return map_faqs_to_public_response(faqs, locale.locale)


# ============================================================================
# Admin Routes - Topics
# ============================================================================


@router.get(
    "/admin/topics",
    response_model=list[TopicResponse],
    summary="List topics (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:read"))],
)
async def list_topics_admin(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[TopicResponse]:
    """List all topics."""
    service = TopicService(db)
    topics = await service.list_topics(tenant_id)
    return [TopicResponse.model_validate(t) for t in topics]


@router.post(
    "/admin/topics",
    response_model=TopicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create topic",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:create"))],
)
async def create_topic(
    data: TopicCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    """Create a new topic."""
    service = TopicService(db)
    topic = await service.create(tenant_id, data)
    return TopicResponse.model_validate(topic)


@router.patch(
    "/admin/topics/{topic_id}",
    response_model=TopicResponse,
    summary="Update topic",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def update_topic(
    topic_id: UUID,
    data: TopicUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TopicResponse:
    """Update a topic."""
    service = TopicService(db)
    topic = await service.update(topic_id, tenant_id, data)
    return TopicResponse.model_validate(topic)


@router.delete(
    "/admin/topics/{topic_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete topic",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:delete"))],
)
async def delete_topic(
    topic_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a topic."""
    service = TopicService(db)
    await service.soft_delete(topic_id, tenant_id)


# ============================================================================
# Admin Routes - Topic Locales
# ============================================================================


@router.post(
    "/admin/topics/{topic_id}/locales",
    response_model=TopicLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to topic",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def create_topic_locale(
    topic_id: UUID,
    data: TopicLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TopicLocaleResponse:
    """Add a new locale to a topic."""
    service = TopicService(db)
    locale = await service.create_locale(topic_id, tenant_id, data)
    return TopicLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/topics/{topic_id}/locales/{locale_id}",
    response_model=TopicLocaleResponse,
    summary="Update topic locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def update_topic_locale(
    topic_id: UUID,
    locale_id: UUID,
    data: TopicLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TopicLocaleResponse:
    """Update a topic locale."""
    service = TopicService(db)
    locale = await service.update_locale(locale_id, topic_id, tenant_id, data)
    return TopicLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/topics/{topic_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete topic locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def delete_topic_locale(
    topic_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from topic (minimum 1 locale required)."""
    service = TopicService(db)
    await service.delete_locale(locale_id, topic_id, tenant_id)


# ============================================================================
# Admin Routes - Articles
# ============================================================================


@router.get(
    "/admin/articles",
    response_model=ArticleListResponse,
    summary="List articles (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:read"))],
)
async def list_articles_admin(
    pagination: Pagination,
    status: str | None = Query(default=None),
    topic_id: UUID | None = Query(default=None, alias="topicId"),
    search: str | None = Query(default=None, description="Search in title, content, slug"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleListResponse:
    """List all articles with filters."""
    service = ArticleService(db)
    articles, total = await service.list_articles(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        topic_id=topic_id,
        search=search,
    )

    return ArticleListResponse(
        items=[ArticleResponse.model_validate(a) for a in articles],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/articles",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create article",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:create"))],
)
async def create_article(
    data: ArticleCreate,
    user: AdminUser = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Create a new article."""
    service = ArticleService(db)
    article = await service.create(tenant_id, data, author_id=user.id)
    return ArticleResponse.model_validate(article)


@router.get(
    "/admin/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Get article",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:read"))],
)
async def get_article_admin(
    article_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Get article by ID."""
    service = ArticleService(db)
    article = await service.get_by_id(article_id, tenant_id)
    return ArticleResponse.model_validate(article)


@router.patch(
    "/admin/articles/{article_id}",
    response_model=ArticleResponse,
    summary="Update article",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def update_article(
    article_id: UUID,
    data: ArticleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Update an article."""
    service = ArticleService(db)
    article = await service.update(article_id, tenant_id, data)
    return ArticleResponse.model_validate(article)


@router.post(
    "/admin/articles/{article_id}/publish",
    response_model=ArticleResponse,
    summary="Publish article",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:publish"))],
)
async def publish_article(
    article_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Publish an article."""
    service = ArticleService(db)
    await service.publish(article_id, tenant_id)
    # Re-fetch article with all relationships to avoid greenlet issues
    article = await service.get_by_id(article_id, tenant_id)
    return ArticleResponse.model_validate(article)


@router.post(
    "/admin/articles/{article_id}/unpublish",
    response_model=ArticleResponse,
    summary="Unpublish article",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:publish"))],
)
async def unpublish_article(
    article_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Unpublish an article (move to draft)."""
    service = ArticleService(db)
    await service.unpublish(article_id, tenant_id)
    # Re-fetch article with all relationships to avoid greenlet issues
    article = await service.get_by_id(article_id, tenant_id)
    return ArticleResponse.model_validate(article)


@router.delete(
    "/admin/articles/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete article",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:delete"))],
)
async def delete_article(
    article_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an article."""
    service = ArticleService(db)
    await service.soft_delete(article_id, tenant_id)


@router.post(
    "/admin/articles/{article_id}/cover-image",
    response_model=ArticleResponse,
    summary="Upload article cover image",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def upload_article_cover_image(
    article_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleResponse:
    """Upload or replace cover image for article.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    service = ArticleService(db)
    article = await service.get_by_id(article_id, tenant_id)
    
    # Upload new image
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="articles",
        entity_id=article_id,
        old_image_url=article.cover_image_url,
    )
    
    # Update article
    article.cover_image_url = new_url
    await db.commit()
    
    # Re-fetch article with all relationships to avoid greenlet issues
    article = await service.get_by_id(article_id, tenant_id)
    
    return ArticleResponse.model_validate(article)


@router.delete(
    "/admin/articles/{article_id}/cover-image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete article cover image",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def delete_article_cover_image(
    article_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete cover image from article."""
    service = ArticleService(db)
    article = await service.get_by_id(article_id, tenant_id)
    
    if article.cover_image_url:
        await image_upload_service.delete_image(article.cover_image_url)
        article.cover_image_url = None
        await db.commit()


# ============================================================================
# Admin Routes - Article Locales
# ============================================================================


@router.post(
    "/admin/articles/{article_id}/locales",
    response_model=ArticleLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to article",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def create_article_locale(
    article_id: UUID,
    data: ArticleLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleLocaleResponse:
    """Add a new locale to an article."""
    service = ArticleService(db)
    locale = await service.create_locale(article_id, tenant_id, data)
    return ArticleLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/articles/{article_id}/locales/{locale_id}",
    response_model=ArticleLocaleResponse,
    summary="Update article locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def update_article_locale(
    article_id: UUID,
    locale_id: UUID,
    data: ArticleLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ArticleLocaleResponse:
    """Update an article locale."""
    service = ArticleService(db)
    locale = await service.update_locale(locale_id, article_id, tenant_id, data)
    return ArticleLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/articles/{article_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete article locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("articles:update"))],
)
async def delete_article_locale(
    article_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from article (minimum 1 locale required)."""
    service = ArticleService(db)
    await service.delete_locale(locale_id, article_id, tenant_id)


# ============================================================================
# Admin Routes - FAQ
# ============================================================================


@router.get(
    "/admin/faq",
    response_model=FAQListResponse,
    summary="List FAQ (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:read"))],
)
async def list_faq_admin(
    pagination: Pagination,
    filtering: Filtering,
    category: str | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQListResponse:
    """List all FAQ items."""
    service = FAQService(db)
    faqs, total = await service.list_faqs(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        category=category,
        is_published=filtering.is_published,
    )

    return FAQListResponse(
        items=[FAQResponse.model_validate(f) for f in faqs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/faq",
    response_model=FAQResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:create"))],
)
async def create_faq(
    data: FAQCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    """Create a new FAQ item."""
    service = FAQService(db)
    faq = await service.create(tenant_id, data)
    return FAQResponse.model_validate(faq)


@router.get(
    "/admin/faq/{faq_id}",
    response_model=FAQResponse,
    summary="Get FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:read"))],
)
async def get_faq_admin(
    faq_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    """Get FAQ by ID."""
    service = FAQService(db)
    faq = await service.get_by_id(faq_id, tenant_id)
    return FAQResponse.model_validate(faq)


@router.patch(
    "/admin/faq/{faq_id}",
    response_model=FAQResponse,
    summary="Update FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def update_faq(
    faq_id: UUID,
    data: FAQUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQResponse:
    """Update a FAQ item."""
    service = FAQService(db)
    faq = await service.update(faq_id, tenant_id, data)
    return FAQResponse.model_validate(faq)


@router.delete(
    "/admin/faq/{faq_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:delete"))],
)
async def delete_faq(
    faq_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a FAQ item."""
    service = FAQService(db)
    await service.soft_delete(faq_id, tenant_id)


# ============================================================================
# Admin Routes - FAQ Locales
# ============================================================================


@router.post(
    "/admin/faq/{faq_id}/locales",
    response_model=FAQLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to FAQ",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def create_faq_locale(
    faq_id: UUID,
    data: FAQLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQLocaleResponse:
    """Add a new locale to a FAQ item."""
    service = FAQService(db)
    locale = await service.create_locale(faq_id, tenant_id, data)
    return FAQLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/faq/{faq_id}/locales/{locale_id}",
    response_model=FAQLocaleResponse,
    summary="Update FAQ locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def update_faq_locale(
    faq_id: UUID,
    locale_id: UUID,
    data: FAQLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FAQLocaleResponse:
    """Update a FAQ locale."""
    service = FAQService(db)
    locale = await service.update_locale(locale_id, faq_id, tenant_id, data)
    return FAQLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/faq/{faq_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete FAQ locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("faq:update"))],
)
async def delete_faq_locale(
    faq_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from FAQ (minimum 1 locale required)."""
    service = FAQService(db)
    await service.delete_locale(locale_id, faq_id, tenant_id)


# ============================================================================
# Public Routes - Cases
# ============================================================================


@router.get(
    "/public/cases",
    response_model=CasePublicListResponse,
    summary="List published cases",
    tags=["Public - Content"],
)
async def list_cases_public(
    locale: Locale,
    pagination: Pagination,
    tenant_id: PublicTenantId,
    featured: bool | None = Query(default=None, description="Filter by featured"),
    db: AsyncSession = Depends(get_db),
) -> CasePublicListResponse:
    """List published cases for public display."""
    service = CaseService(db)
    cases, total = await service.list_published(
        tenant_id=tenant_id,
        locale=locale.locale,
        page=pagination.page,
        page_size=pagination.page_size,
        is_featured=featured,
    )

    items = map_cases_to_public_response(cases, locale.locale, include_full_content=False)

    return CasePublicListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/public/cases/{slug}",
    response_model=CasePublicResponse,
    summary="Get case by slug",
    tags=["Public - Content"],
)
async def get_case_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> CasePublicResponse:
    """Get a published case by slug."""
    service = CaseService(db)
    case = await service.get_by_slug(slug, locale.locale, tenant_id)
    return map_case_to_public_response(case, locale.locale, include_full_content=True)


# ============================================================================
# Admin Routes - Cases
# ============================================================================


@router.get(
    "/admin/cases",
    response_model=CaseListResponse,
    summary="List cases (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:read"))],
)
async def list_cases_admin(
    pagination: Pagination,
    status: str | None = Query(default=None),
    featured: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Search in title and client name"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    """List all cases with filters."""
    service = CaseService(db)
    cases, total = await service.list_cases(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        is_featured=featured,
        search=search,
    )

    return CaseListResponse(
        items=[CaseResponse.model_validate(c) for c in cases],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/cases",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:create"))],
)
async def create_case(
    data: CaseCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Create a new case."""
    service = CaseService(db)
    case = await service.create(tenant_id, data)
    return CaseResponse.model_validate(case)


@router.get(
    "/admin/cases/{case_id}",
    response_model=CaseResponse,
    summary="Get case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:read"))],
)
async def get_case_admin(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Get case by ID."""
    service = CaseService(db)
    case = await service.get_by_id(case_id, tenant_id)
    return CaseResponse.model_validate(case)


@router.patch(
    "/admin/cases/{case_id}",
    response_model=CaseResponse,
    summary="Update case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def update_case(
    case_id: UUID,
    data: CaseUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Update a case."""
    service = CaseService(db)
    case = await service.update(case_id, tenant_id, data)
    return CaseResponse.model_validate(case)


@router.post(
    "/admin/cases/{case_id}/publish",
    response_model=CaseResponse,
    summary="Publish case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:publish"))],
)
async def publish_case(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Publish a case."""
    service = CaseService(db)
    await service.publish(case_id, tenant_id)
    # Re-fetch case with all relationships to avoid greenlet issues
    case = await service.get_by_id(case_id, tenant_id)
    return CaseResponse.model_validate(case)


@router.post(
    "/admin/cases/{case_id}/unpublish",
    response_model=CaseResponse,
    summary="Unpublish case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:publish"))],
)
async def unpublish_case(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Unpublish a case (move to draft)."""
    service = CaseService(db)
    await service.unpublish(case_id, tenant_id)
    # Re-fetch case with all relationships to avoid greenlet issues
    case = await service.get_by_id(case_id, tenant_id)
    return CaseResponse.model_validate(case)


@router.delete(
    "/admin/cases/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:delete"))],
)
async def delete_case(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a case."""
    service = CaseService(db)
    await service.soft_delete(case_id, tenant_id)


@router.post(
    "/admin/cases/{case_id}/cover-image",
    response_model=CaseResponse,
    summary="Upload case cover image",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def upload_case_cover_image(
    case_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseResponse:
    """Upload or replace cover image for case.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    service = CaseService(db)
    case = await service.get_by_id(case_id, tenant_id)
    
    # Upload new image
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="cases",
        entity_id=case_id,
        old_image_url=case.cover_image_url,
    )
    
    # Update case
    case.cover_image_url = new_url
    await db.commit()
    
    # Re-fetch case with all relationships to avoid greenlet issues
    case = await service.get_by_id(case_id, tenant_id)
    
    return CaseResponse.model_validate(case)


@router.delete(
    "/admin/cases/{case_id}/cover-image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case cover image",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def delete_case_cover_image(
    case_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete cover image from case."""
    service = CaseService(db)
    case = await service.get_by_id(case_id, tenant_id)
    
    if case.cover_image_url:
        await image_upload_service.delete_image(case.cover_image_url)
        case.cover_image_url = None
        await db.commit()


# ============================================================================
# Admin Routes - Case Locales
# ============================================================================


@router.post(
    "/admin/cases/{case_id}/locales",
    response_model=CaseLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to case",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def create_case_locale(
    case_id: UUID,
    data: CaseLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseLocaleResponse:
    """Add a new locale to a case."""
    service = CaseService(db)
    locale = await service.create_locale(case_id, tenant_id, data)
    return CaseLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/cases/{case_id}/locales/{locale_id}",
    response_model=CaseLocaleResponse,
    summary="Update case locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def update_case_locale(
    case_id: UUID,
    locale_id: UUID,
    data: CaseLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CaseLocaleResponse:
    """Update a case locale."""
    service = CaseService(db)
    locale = await service.update_locale(locale_id, case_id, tenant_id, data)
    return CaseLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/cases/{case_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete case locale",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("cases:update"))],
)
async def delete_case_locale(
    case_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from case (minimum 1 locale required)."""
    service = CaseService(db)
    await service.delete_locale(locale_id, case_id, tenant_id)


# ============================================================================
# Public Routes - Reviews
# ============================================================================


@router.get(
    "/public/reviews",
    response_model=ReviewPublicListResponse,
    summary="List approved reviews",
    tags=["Public - Content"],
)
async def list_reviews_public(
    pagination: Pagination,
    tenant_id: PublicTenantId,
    case_id: UUID | None = Query(default=None, alias="caseId"),
    featured: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ReviewPublicListResponse:
    """List approved reviews for public display."""
    service = ReviewService(db)
    reviews, total = await service.list_approved(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        case_id=case_id,
        is_featured=featured,
    )

    items = [
        ReviewPublicResponse(
            id=r.id,
            rating=r.rating,
            author_name=r.author_name,
            author_company=r.author_company,
            author_position=r.author_position,
            author_photo_url=r.author_photo_url,
            content=r.content,
            source=r.source,
            review_date=r.review_date,
        )
        for r in reviews
    ]

    return ReviewPublicListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


# ============================================================================
# Admin Routes - Reviews
# ============================================================================


@router.get(
    "/admin/reviews",
    response_model=ReviewListResponse,
    summary="List reviews (admin)",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:read"))],
)
async def list_reviews_admin(
    pagination: Pagination,
    status: str | None = Query(default=None),
    case_id: UUID | None = Query(default=None, alias="caseId"),
    featured: bool | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewListResponse:
    """List all reviews with filters."""
    service = ReviewService(db)
    reviews, total = await service.list_reviews(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        case_id=case_id,
        is_featured=featured,
    )

    return ReviewListResponse(
        items=[ReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:create"))],
)
async def create_review(
    data: ReviewCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Create a new review."""
    service = ReviewService(db)
    review = await service.create(tenant_id, data)
    return ReviewResponse.model_validate(review)


@router.get(
    "/admin/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Get review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:read"))],
)
async def get_review_admin(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Get review by ID."""
    service = ReviewService(db)
    review = await service.get_by_id(review_id, tenant_id)
    return ReviewResponse.model_validate(review)


@router.patch(
    "/admin/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="Update review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def update_review(
    review_id: UUID,
    data: ReviewUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Update a review."""
    service = ReviewService(db)
    review = await service.update(review_id, tenant_id, data)
    return ReviewResponse.model_validate(review)


@router.post(
    "/admin/reviews/{review_id}/approve",
    response_model=ReviewResponse,
    summary="Approve review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def approve_review(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Approve a review for public display."""
    service = ReviewService(db)
    review = await service.approve(review_id, tenant_id)
    return ReviewResponse.model_validate(review)


@router.post(
    "/admin/reviews/{review_id}/reject",
    response_model=ReviewResponse,
    summary="Reject review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def reject_review(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Reject a review."""
    service = ReviewService(db)
    review = await service.reject(review_id, tenant_id)
    return ReviewResponse.model_validate(review)


@router.delete(
    "/admin/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:delete"))],
)
async def delete_review(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a review."""
    service = ReviewService(db)
    await service.soft_delete(review_id, tenant_id)


@router.post(
    "/admin/reviews/{review_id}/author-photo",
    response_model=ReviewResponse,
    summary="Upload review author photo",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def upload_review_author_photo(
    review_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Upload or replace author photo for review.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    service = ReviewService(db)
    review = await service.get_by_id(review_id, tenant_id)
    
    # Upload new image
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="reviews",
        entity_id=review_id,
        old_image_url=review.author_photo_url,
    )
    
    # Update review
    review.author_photo_url = new_url
    await db.commit()
    
    # Re-fetch review to avoid greenlet issues
    review = await service.get_by_id(review_id, tenant_id)
    
    return ReviewResponse.model_validate(review)


@router.delete(
    "/admin/reviews/{review_id}/author-photo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete review author photo",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("reviews:update"))],
)
async def delete_review_author_photo(
    review_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete author photo from review."""
    service = ReviewService(db)
    review = await service.get_by_id(review_id, tenant_id)
    
    if review.author_photo_url:
        await image_upload_service.delete_image(review.author_photo_url)
        review.author_photo_url = None
        await db.commit()


# ============================================================================
# Admin Routes - Bulk Operations
# ============================================================================


@router.post(
    "/admin/bulk",
    response_model=BulkOperationResponse,
    summary="Bulk operations",
    tags=["Admin - Content"],
    dependencies=[Depends(PermissionChecker("content:bulk"))],
)
async def bulk_operation(
    data: BulkOperationRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> BulkOperationResponse:
    """Execute bulk operations on content.

    Supported resource types:
    - articles: Publish, unpublish, archive, delete
    - cases: Publish, unpublish, archive, delete
    - faq: Publish, unpublish, delete
    - reviews: Publish (approve), unpublish (reject), delete

    Items are processed synchronously for < 100 items.
    For larger batches, consider implementing async processing with Celery.
    """
    service = BulkOperationService(db)
    summary = await service.execute(tenant_id, data)

    return BulkOperationResponse(
        job_id=None,
        status="completed",
        summary=summary,
    )

