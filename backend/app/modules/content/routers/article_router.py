"""Article routes for content module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_active_user, get_current_tenant_id
from app.modules.auth.models import AdminUser
from app.modules.content.mappers import (
    map_article_to_public_response,
    map_articles_to_public_response,
)
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
)
from app.modules.content.service import ArticleService

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
    article_status: str | None = Query(default=None, alias="status"),
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
        status=article_status,
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
    """Upload or replace cover image for article."""
    service = ArticleService(db)
    article = await service.get_by_id(article_id, tenant_id)
    
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="articles",
        entity_id=article_id,
        old_image_url=article.cover_image_url,
    )
    
    article.cover_image_url = new_url
    await db.commit()
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
