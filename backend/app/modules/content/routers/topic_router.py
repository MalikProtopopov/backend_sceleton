"""Topic routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Locale, PublicTenantId
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.content.mappers import (
    map_topic_to_detail_public_response,
    map_topics_with_counts_to_public_response,
)
from app.modules.content.schemas import (
    TopicCreate,
    TopicDetailPublicResponse,
    TopicLocaleCreate,
    TopicLocaleResponse,
    TopicLocaleUpdate,
    TopicResponse,
    TopicUpdate,
    TopicWithArticlesCountPublicResponse,
)
from app.modules.content.service import TopicService

router = APIRouter()


# ============================================================================
# Public Routes - Topics
# ============================================================================


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
    """List all topics with article count."""
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
    """Get topic details by slug."""
    service = TopicService(db)
    topic = await service.get_by_slug(slug, locale.locale, tenant_id)
    articles_count = await service.count_articles(topic.id)
    return map_topic_to_detail_public_response(topic, locale.locale, articles_count)


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
    status_code=201,
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
    status_code=204,
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
    status_code=201,
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
    status_code=204,
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
