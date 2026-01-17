"""API routes for SEO module."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, PublicTenantId
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.seo.schemas import (
    RedirectCreate,
    RedirectListResponse,
    RedirectResponse,
    RedirectUpdate,
    SEOMetaResponse,
    SEORouteCreate,
    SEORouteResponse,
    SEORouteUpdate,
)
from app.modules.seo.service import RedirectService, SEORouteService, SitemapService

router = APIRouter()


# ============================================================================
# Public Routes
# ============================================================================


@router.get(
    "/public/seo/meta",
    response_model=SEOMetaResponse,
    summary="Get SEO meta for path",
    tags=["Public - SEO"],
)
async def get_seo_meta(
    tenant_id: PublicTenantId,
    path: str = Query(..., description="Page path"),
    locale: str = Query(default="ru", description="Locale"),
    db: AsyncSession = Depends(get_db),
) -> SEOMetaResponse:
    """Get SEO metadata for a specific path."""
    service = SEORouteService(db)
    route = await service.get_by_path(path, locale, tenant_id)

    if not route:
        return SEOMetaResponse()

    return SEOMetaResponse(
        title=route.title,
        meta_title=route.meta_title,
        meta_description=route.meta_description,
        meta_keywords=route.meta_keywords,
        og_image=route.og_image,
        canonical_url=route.canonical_url,
        robots=route.robots_meta,
        structured_data=route.structured_data,
    )


@router.get(
    "/public/sitemap.xml",
    response_class=PlainTextResponse,
    summary="Get sitemap.xml",
    tags=["Public - SEO"],
)
async def get_sitemap(
    request: Request,
    tenant_id: PublicTenantId,
    locale: str = Query(default="ru", description="Locale"),
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Generate and return sitemap.xml."""
    service = SitemapService(db)

    # Build base URL from request
    base_url = f"{request.url.scheme}://{request.url.netloc}"

    xml = await service.generate_sitemap_xml(tenant_id, locale, base_url)

    return PlainTextResponse(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get(
    "/public/robots.txt",
    response_class=PlainTextResponse,
    summary="Get robots.txt",
    tags=["Public - SEO"],
)
async def get_robots(
    request: Request,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Generate and return robots.txt."""
    service = SitemapService(db)

    base_url = f"{request.url.scheme}://{request.url.netloc}"
    sitemap_url = f"{base_url}/api/v1/public/sitemap.xml?tenant_id={tenant_id}"

    content = service.generate_robots_txt(base_url, sitemap_url)

    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=86400"},
    )


# ============================================================================
# Admin Routes - SEO Routes
# ============================================================================


@router.get(
    "/admin/seo/routes",
    response_model=list[SEORouteResponse],
    summary="List SEO routes",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:read"))],
)
async def list_seo_routes(
    pagination: Pagination,
    locale: str | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[SEORouteResponse]:
    """List all SEO routes."""
    service = SEORouteService(db)
    routes, _ = await service.list_routes(
        tenant_id=tenant_id,
        locale=locale,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return [SEORouteResponse.model_validate(r) for r in routes]


@router.put(
    "/admin/seo/routes",
    response_model=SEORouteResponse,
    summary="Create or update SEO route",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:update"))],
)
async def upsert_seo_route(
    data: SEORouteCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> SEORouteResponse:
    """Create or update SEO metadata for a path."""
    service = SEORouteService(db)
    route = await service.create_or_update(tenant_id, data)
    return SEORouteResponse.model_validate(route)


@router.patch(
    "/admin/seo/routes/{route_id}",
    response_model=SEORouteResponse,
    summary="Update SEO route",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:update"))],
)
async def update_seo_route(
    route_id: UUID,
    data: SEORouteUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> SEORouteResponse:
    """Update SEO route."""
    service = SEORouteService(db)
    route = await service.update(route_id, tenant_id, data)
    return SEORouteResponse.model_validate(route)


@router.delete(
    "/admin/seo/routes/{route_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete SEO route",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:update"))],
)
async def delete_seo_route(
    route_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete SEO route."""
    service = SEORouteService(db)
    await service.delete(route_id, tenant_id)


# ============================================================================
# Admin Routes - Redirects
# ============================================================================


@router.get(
    "/admin/seo/redirects",
    response_model=RedirectListResponse,
    summary="List redirects",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:read"))],
)
async def list_redirects(
    pagination: Pagination,
    is_active: bool | None = Query(default=None, alias="isActive"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RedirectListResponse:
    """List all redirects."""
    service = RedirectService(db)
    redirects, total = await service.list_redirects(
        tenant_id=tenant_id,
        is_active=is_active,
        page=pagination.page,
        page_size=pagination.page_size,
    )

    return RedirectListResponse(
        items=[RedirectResponse.model_validate(r) for r in redirects],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/seo/redirects",
    response_model=RedirectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create redirect",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:update"))],
)
async def create_redirect(
    data: RedirectCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Create a new redirect."""
    service = RedirectService(db)
    redirect = await service.create(tenant_id, data)
    return RedirectResponse.model_validate(redirect)


@router.get(
    "/admin/seo/redirects/{redirect_id}",
    response_model=RedirectResponse,
    summary="Get redirect",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:read"))],
)
async def get_redirect(
    redirect_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Get redirect by ID."""
    service = RedirectService(db)
    redirect = await service.get_by_id(redirect_id, tenant_id)
    return RedirectResponse.model_validate(redirect)


@router.patch(
    "/admin/seo/redirects/{redirect_id}",
    response_model=RedirectResponse,
    summary="Update redirect",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:update"))],
)
async def update_redirect(
    redirect_id: UUID,
    data: RedirectUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Update a redirect."""
    service = RedirectService(db)
    redirect = await service.update(redirect_id, tenant_id, data)
    return RedirectResponse.model_validate(redirect)


@router.delete(
    "/admin/seo/redirects/{redirect_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete redirect",
    tags=["Admin - SEO"],
    dependencies=[Depends(PermissionChecker("seo:update"))],
)
async def delete_redirect(
    redirect_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a redirect."""
    service = RedirectService(db)
    await service.soft_delete(redirect_id, tenant_id)

