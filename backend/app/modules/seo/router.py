"""API routes for SEO module."""

from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, PublicTenantId
from app.core.logging import get_logger
from app.core.security import PermissionChecker, get_current_tenant_id
from app.middleware.feature_check import require_seo_advanced
from app.modules.seo.utils import normalize_path, validate_base_url, extract_domain
from app.modules.seo.schemas import (
    RedirectCreate,
    RedirectExportItem,
    RedirectExportResponse,
    RedirectListResponse,
    RedirectResponse,
    RedirectUpdate,
    RevalidateRequest,
    RevalidateResponse,
    SEOMetaResponse,
    SEORouteCreate,
    SEORouteResponse,
    SEORouteUpdate,
)
from app.modules.seo.service import RedirectService, SEORouteService, SitemapService
from app.modules.tenants.service import TenantService

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Cache header constants
# ============================================================================

# Cache-Control values following plan spec
CACHE_SEO_META_FOUND = "public, max-age=60, s-maxage=600, stale-while-revalidate=86400"
CACHE_SEO_META_NOT_FOUND = "public, max-age=30, s-maxage=300"
CACHE_SITEMAP = "public, max-age=600, s-maxage=3600, stale-while-revalidate=86400"
CACHE_ROBOTS = "public, max-age=3600, s-maxage=86400"
CACHE_REDIRECTS = "public, max-age=60, s-maxage=600, stale-while-revalidate=86400"


def format_http_date(dt: datetime | None) -> str | None:
    """Format datetime as HTTP date header value."""
    if dt is None:
        return None
    # Ensure timezone-aware UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


async def get_validated_base_url(
    request: Request,
    tenant_id: UUID,
    db: AsyncSession,
) -> str:
    """Get and validate base URL from request against tenant's allowed domains.
    
    If the request domain is not in allowed_domains, falls back to tenant's primary domain.
    """
    request_base_url = f"{request.url.scheme}://{request.url.netloc}"
    request_domain = extract_domain(request_base_url)
    
    # Get tenant settings
    tenant_service = TenantService(db)
    try:
        tenant = await tenant_service.get_by_id(tenant_id)
    except Exception:
        # If tenant not found, just use request URL
        return request_base_url
    
    # Get allowed domains from settings
    allowed_domains = None
    if tenant.settings:
        allowed_domains = tenant.settings.allowed_domains
    
    # If no allowed domains configured, also check tenant's primary domain
    if not allowed_domains:
        if tenant.domain:
            allowed_domains = [tenant.domain]
        else:
            # No restrictions, accept any domain
            return request_base_url
    
    # Validate request domain
    is_valid, _ = validate_base_url(request_base_url, allowed_domains)
    
    if is_valid:
        return request_base_url
    
    # Domain not in whitelist - use tenant's primary domain or first allowed domain
    logger.warning(
        "domain_not_in_whitelist",
        request_domain=request_domain,
        tenant_id=str(tenant_id),
        allowed_domains=allowed_domains,
    )
    
    # Prefer tenant's primary domain
    if tenant.domain:
        return f"{request.url.scheme}://{tenant.domain}"
    
    # Fall back to first allowed domain (without wildcards)
    for domain in allowed_domains:
        if not domain.startswith("*."):
            return f"{request.url.scheme}://{domain}"
    
    # Last resort: use request URL
    return request_base_url


async def get_base_url_for_sitemap(
    request: Request,
    tenant_id: UUID,
    db: AsyncSession,
) -> tuple[str, bool]:
    """Get base URL for sitemap/robots: prefer tenant site_url (frontend), else request URL.
    
    Returns:
        (base_url, is_frontend): is_frontend True when site_url was used (for robots Sitemap:).
    """
    tenant_service = TenantService(db)
    try:
        tenant = await tenant_service.get_by_id(tenant_id)
    except Exception:
        base_url = await get_validated_base_url(request, tenant_id, db)
        return base_url, False
    if tenant.settings and tenant.settings.site_url and tenant.settings.site_url.strip():
        site_url = tenant.settings.site_url.strip().rstrip("/")
        if site_url.startswith("http://") or site_url.startswith("https://"):
            return site_url, True
    base_url = await get_validated_base_url(request, tenant_id, db)
    return base_url, False


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
    response: Response,
    tenant_id: PublicTenantId,
    path: str = Query(..., description="Page path"),
    locale: str = Query(default="ru", description="Locale"),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    db: AsyncSession = Depends(get_db),
):
    """Get SEO metadata for a specific path.
    
    Returns semantic ETag and Last-Modified headers for efficient caching.
    Path is normalized before lookup.
    """
    service = SEORouteService(db)
    normalized = normalize_path(path)
    route = await service.get_by_path(normalized, locale, tenant_id)

    if not route:
        # No route found - return empty response with shorter cache
        response.headers["Cache-Control"] = CACHE_SEO_META_NOT_FOUND
        return SEOMetaResponse(normalized_path=normalized)

    # Generate semantic ETag
    ts = int(route.updated_at.timestamp()) if route.updated_at else 0
    etag = f'W/"seo-meta:{tenant_id}:{locale}:{normalized}:{ts}"'
    
    # Check conditional request
    if if_none_match and if_none_match == etag:
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": CACHE_SEO_META_FOUND,
            },
        )
    
    # Set caching headers
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = CACHE_SEO_META_FOUND
    if route.updated_at:
        last_modified = format_http_date(route.updated_at)
        if last_modified:
            response.headers["Last-Modified"] = last_modified

    return SEOMetaResponse(
        title=route.title,
        meta_title=route.meta_title,
        meta_description=route.meta_description,
        meta_keywords=route.meta_keywords,
        og_image=route.og_image,
        canonical_url=route.canonical_url,
        robots=route.robots_meta,
        structured_data=route.structured_data,
        normalized_path=normalized,
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
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return sitemap.xml.
    
    Returns semantic ETag and Last-Modified headers for efficient caching.
    Base URL is validated against tenant's allowed domains.
    """
    service = SitemapService(db)

    # Get metadata for caching
    metadata = await service.get_sitemap_metadata(tenant_id, locale)
    
    # Check conditional request
    if if_none_match and metadata.etag and if_none_match == metadata.etag:
        return Response(
            status_code=304,
            headers={
                "ETag": metadata.etag,
                "Cache-Control": CACHE_SITEMAP,
            },
        )

    # Get base URL (prefer tenant site_url for frontend domain in <loc>)
    base_url, _ = await get_base_url_for_sitemap(request, tenant_id, db)

    xml = await service.generate_sitemap_xml(tenant_id, locale, base_url)

    headers = {
        "Cache-Control": CACHE_SITEMAP,
    }
    
    if metadata.etag:
        headers["ETag"] = metadata.etag
    
    if metadata.last_modified:
        last_modified = format_http_date(metadata.last_modified)
        if last_modified:
            headers["Last-Modified"] = last_modified

    return PlainTextResponse(
        content=xml,
        media_type="application/xml",
        headers=headers,
    )


@router.get(
    "/public/sitemap-index.xml",
    response_class=PlainTextResponse,
    summary="Get sitemap index",
    tags=["Public - SEO"],
)
async def get_sitemap_index(
    request: Request,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """Generate and return sitemap index referencing segment sitemaps.
    
    This endpoint returns a sitemap index that references individual
    segment sitemaps for each locale (e.g., sitemap-articles-ru.xml).
    """
    service = SitemapService(db)
    
    # Get base URL (prefer tenant site_url for frontend domain)
    base_url, _ = await get_base_url_for_sitemap(request, tenant_id, db)
    
    # Default locales - could be fetched from tenant settings
    locales = ["ru", "en"]
    
    xml = service.generate_sitemap_index_xml(base_url, tenant_id, locales)
    
    return PlainTextResponse(
        content=xml,
        media_type="application/xml",
        headers={"Cache-Control": CACHE_SITEMAP},
    )


@router.get(
    "/public/sitemap-{segment}-{locale}.xml",
    response_class=PlainTextResponse,
    summary="Get segment sitemap",
    tags=["Public - SEO"],
)
async def get_segment_sitemap(
    request: Request,
    tenant_id: PublicTenantId,
    segment: str,
    locale: str,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return sitemap for a specific segment and locale.
    
    Segments:
    - pages: Static pages + SEO routes
    - articles: Blog articles + topics
    - cases: Portfolio cases
    - services: Services
    - team: Team members
    - documents: Documents
    """
    # Validate segment
    valid_segments = ["pages", "articles", "cases", "services", "team", "documents"]
    if segment not in valid_segments:
        return PlainTextResponse(
            content=f"Invalid segment. Valid segments: {', '.join(valid_segments)}",
            status_code=400,
        )
    
    service = SitemapService(db)
    
    # Get metadata for caching
    metadata = await service.get_sitemap_metadata(tenant_id, locale)
    
    # Modify ETag to include segment
    segment_etag = metadata.etag.replace('sitemap:', f'sitemap-{segment}:') if metadata.etag else None
    
    # Check conditional request
    if if_none_match and segment_etag and if_none_match == segment_etag:
        return Response(
            status_code=304,
            headers={
                "ETag": segment_etag,
                "Cache-Control": CACHE_SITEMAP,
            },
        )
    
    # Get base URL (prefer tenant site_url for frontend domain)
    base_url, _ = await get_base_url_for_sitemap(request, tenant_id, db)
    
    xml = await service.generate_segment_sitemap_xml(tenant_id, locale, base_url, segment)
    
    headers = {
        "Cache-Control": CACHE_SITEMAP,
    }
    
    if segment_etag:
        headers["ETag"] = segment_etag
    
    if metadata.last_modified:
        last_modified = format_http_date(metadata.last_modified)
        if last_modified:
            headers["Last-Modified"] = last_modified
    
    return PlainTextResponse(
        content=xml,
        media_type="application/xml",
        headers=headers,
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
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return robots.txt.
    
    Returns ETag header for efficient caching.
    Base URL is validated against tenant's allowed domains.
    Includes custom rules from TenantSettings if configured.
    """
    service = SitemapService(db)
    tenant_service = TenantService(db)

    # Get base URL (prefer tenant site_url so Sitemap: points to frontend)
    base_url, is_frontend = await get_base_url_for_sitemap(request, tenant_id, db)
    if is_frontend:
        sitemap_url = f"{base_url}/sitemap.xml"
    else:
        sitemap_url = f"{base_url}/api/v1/public/sitemap.xml?tenant_id={tenant_id}"
    
    # Get custom rules from tenant settings
    custom_rules = None
    try:
        settings = await tenant_service.get_settings(tenant_id)
        if settings:
            custom_rules = settings.robots_txt_custom_rules
    except Exception:
        pass  # If settings not found, use default rules

    content = service.generate_robots_txt(base_url, sitemap_url, custom_rules)
    
    # Generate ETag based on content
    import hashlib
    content_hash = hashlib.md5(content.encode()).hexdigest()[:16]
    etag = f'W/"robots:{tenant_id}:{content_hash}"'
    
    # Check conditional request
    if if_none_match and if_none_match == etag:
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": CACHE_ROBOTS,
            },
        )

    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={
            "Cache-Control": CACHE_ROBOTS,
            "ETag": etag,
        },
    )


@router.get(
    "/public/seo/redirects",
    response_model=RedirectExportResponse,
    summary="Get redirects for edge/proxy",
    tags=["Public - SEO"],
)
async def get_redirects_export(
    response: Response,
    tenant_id: PublicTenantId,
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    db: AsyncSession = Depends(get_db),
):
    """Get all active redirects for edge/proxy consumption.
    
    This endpoint is designed to be polled by edge workers, proxies,
    or Next.js middleware to apply redirects without hitting the
    database on every request.
    
    Returns:
        - generated_at: Timestamp of when the export was generated
        - etag: Semantic ETag for cache validation
        - redirects: List of active redirects with source_path, target_url, type
    """
    service = RedirectService(db)
    
    # Get active redirects and metadata
    redirects, max_updated_at = await service.list_active_for_export(tenant_id)
    
    # Generate semantic ETag
    ts = int(max_updated_at.timestamp()) if max_updated_at else 0
    count = len(redirects)
    etag = f'W/"redirects:{tenant_id}:{ts}:{count}"'
    
    # Check conditional request
    if if_none_match and if_none_match == etag:
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": CACHE_REDIRECTS,
            },
        )
    
    # Set response headers
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = CACHE_REDIRECTS
    if max_updated_at:
        last_modified = format_http_date(max_updated_at)
        if last_modified:
            response.headers["Last-Modified"] = last_modified
    
    # Build response
    redirect_items = [
        RedirectExportItem(
            source_path=r.source_path,
            target_url=r.target_url,
            redirect_type=r.redirect_type,
            is_active=r.is_active,
        )
        for r in redirects
    ]
    
    return RedirectExportResponse(
        generated_at=datetime.now(UTC),
        etag=etag,
        redirects=redirect_items,
    )


@router.get(
    "/public/indexnow/{key}.txt",
    response_class=PlainTextResponse,
    summary="IndexNow key verification file",
    tags=["Public - SEO"],
)
async def get_indexnow_key_file(
    key: str,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Serve IndexNow key verification file.
    
    IndexNow requires the key file to be accessible at /{key}.txt
    for domain verification.
    """
    from app.modules.seo.indexnow_service import IndexNowService
    
    service = IndexNowService(db)
    stored_key = await service.get_key(tenant_id)
    
    # Verify the requested key matches the tenant's key
    if not stored_key or key != stored_key:
        return Response(
            status_code=404,
            content="Not Found",
        )
    
    return PlainTextResponse(
        content=key,
        media_type="text/plain",
        headers={
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.get(
    "/public/llms.txt",
    response_class=PlainTextResponse,
    summary="Get llms.txt for AI discovery",
    tags=["Public - SEO"],
)
async def get_llms_txt(
    request: Request,
    tenant_id: PublicTenantId,
    locale: str = Query(default="en", description="Locale for content"),
    db: AsyncSession = Depends(get_db),
):
    """Generate and return llms.txt for AI discovery.
    
    llms.txt is a curated markdown file that helps AI systems
    understand the structure and content of the website for
    better citations and references to primary sources.
    
    Specification: https://llmstxt.org/
    """
    from app.modules.seo.llms_service import LlmsTxtService
    
    service = LlmsTxtService(db)
    
    # Check if enabled
    if not await service.is_enabled(tenant_id):
        return Response(
            status_code=404,
            content="llms.txt not enabled for this tenant",
        )
    
    # Get validated base URL
    base_url = await get_validated_base_url(request, tenant_id, db)
    
    content = await service.generate(tenant_id, locale, base_url)
    
    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


# ============================================================================
# Admin Routes - SEO Management
# ============================================================================


@router.post(
    "/admin/seo/revalidate",
    response_model=RevalidateResponse,
    summary="Trigger cache revalidation",
    tags=["Admin - SEO"],
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:update"))],
)
async def revalidate_seo_cache(
    data: RevalidateRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RevalidateResponse:
    """Trigger cache revalidation for SEO resources.
    
    This endpoint can be used to:
    - Invalidate sitemap caches after content changes
    - Force regeneration of robots.txt
    - Clear redirect cache for edge/proxy
    - Trigger frontend revalidation (if configured)
    
    Targets:
    - sitemap: Invalidate sitemap caches
    - robots: Invalidate robots.txt cache
    - redirects: Invalidate redirect export cache
    - meta: Invalidate SEO meta caches
    - all: Invalidate all caches
    """
    # Determine effective targets
    targets = data.targets
    if "all" in targets:
        targets = ["sitemap", "robots", "redirects", "meta"]
    
    # Log the revalidation request
    logger.info(
        "seo_cache_revalidate",
        tenant_id=str(tenant_id),
        targets=targets,
        notify_frontend=data.notify_frontend,
    )
    
    # In a production setup with Redis/CDN, you would:
    # 1. Clear internal caches (Redis keys)
    # 2. Purge CDN cache for relevant paths
    # 3. Optionally call frontend revalidation webhook
    
    # For now, we just return success - the actual cache invalidation
    # happens automatically via ETag changes when content is updated
    
    # If notify_frontend is enabled, call the frontend revalidation webhook
    if data.notify_frontend:
        # This would be implemented to call a frontend webhook
        # Example: await notify_frontend_revalidation(tenant_id, targets)
        pass
    
    return RevalidateResponse(
        success=True,
        message=f"Cache revalidation triggered for: {', '.join(targets)}",
        targets=targets,
        timestamp=datetime.now(UTC),
    )


# ============================================================================
# Admin Routes - SEO Routes
# ============================================================================


@router.get(
    "/admin/seo/routes",
    response_model=list[SEORouteResponse],
    summary="List SEO routes",
    tags=["Admin - SEO"],
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:read"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:update"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:update"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:update"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:read"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:update"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:read"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:update"))],
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
    dependencies=[require_seo_advanced, Depends(PermissionChecker("seo:update"))],
)
async def delete_redirect(
    redirect_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a redirect."""
    service = RedirectService(db)
    await service.soft_delete(redirect_id, tenant_id)

