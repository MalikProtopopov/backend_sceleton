"""SEO module service layer."""

from datetime import datetime, UTC
from uuid import UUID
from xml.sax.saxutils import escape as xml_escape

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.core.url_utils import normalize_path, build_sitemap_url
from app.modules.seo.models import Redirect, SEORoute
from app.modules.seo.schemas import (
    RedirectCreate,
    RedirectUpdate,
    SEORouteCreate,
    SEORouteUpdate,
    SitemapMetadata,
)


class SEORouteService:
    """Service for managing SEO routes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_path(
        self, path: str, locale: str, tenant_id: UUID
    ) -> SEORoute | None:
        """Get SEO route by path and locale.
        
        Path is normalized before lookup.
        """
        normalized = normalize_path(path)
        stmt = (
            select(SEORoute)
            .where(SEORoute.tenant_id == tenant_id)
            .where(SEORoute.path == normalized)
            .where(SEORoute.locale == locale)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, route_id: UUID, tenant_id: UUID) -> SEORoute:
        """Get SEO route by ID."""
        stmt = (
            select(SEORoute)
            .where(SEORoute.id == route_id)
            .where(SEORoute.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        route = result.scalar_one_or_none()

        if not route:
            raise NotFoundError("SEORoute", route_id)

        return route

    async def list_routes(
        self,
        tenant_id: UUID,
        locale: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SEORoute], int]:
        """List SEO routes."""
        base_query = select(SEORoute).where(SEORoute.tenant_id == tenant_id)

        if locale:
            base_query = base_query.where(SEORoute.locale == locale)

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.order_by(SEORoute.path)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        routes = list(result.scalars().all())

        return routes, total

    async def get_sitemap_urls(
        self, tenant_id: UUID, locale: str
    ) -> list[SEORoute]:
        """Get all URLs for sitemap."""
        stmt = (
            select(SEORoute)
            .where(SEORoute.tenant_id == tenant_id)
            .where(SEORoute.locale == locale)
            .where(SEORoute.include_in_sitemap.is_(True))
            .order_by(SEORoute.sitemap_priority.desc().nullslast())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_sitemap_metadata(
        self, tenant_id: UUID, locale: str
    ) -> SitemapMetadata:
        """Get sitemap metadata for caching (last_modified, count).
        
        Used to generate semantic ETag and Last-Modified headers.
        """
        stmt = (
            select(
                func.max(SEORoute.updated_at).label("last_modified"),
                func.count().label("total_count"),
            )
            .where(SEORoute.tenant_id == tenant_id)
            .where(SEORoute.locale == locale)
            .where(SEORoute.include_in_sitemap.is_(True))
        )
        result = await self.db.execute(stmt)
        row = result.one()
        
        last_modified = row.last_modified
        total_count = row.total_count or 0
        
        # Generate semantic ETag
        ts = int(last_modified.timestamp()) if last_modified else 0
        etag = f'W/"sitemap:{tenant_id}:{locale}:{ts}:{total_count}"'
        
        return SitemapMetadata(
            last_modified=last_modified,
            total_count=total_count,
            etag=etag,
        )

    @transactional
    async def create_or_update(
        self, tenant_id: UUID, data: SEORouteCreate
    ) -> SEORoute:
        """Create or update SEO route for a path.
        
        Path is normalized before storage.
        """
        # Normalize path before storage
        normalized_path = normalize_path(data.path)
        data_dict = data.model_dump()
        data_dict["path"] = normalized_path
        
        existing = await self.get_by_path(normalized_path, data.locale, tenant_id)

        if existing:
            # Update existing
            for field, value in data_dict.items():
                setattr(existing, field, value)
            route = existing
        else:
            # Create new
            route = SEORoute(tenant_id=tenant_id, **data_dict)
            self.db.add(route)

        await self.db.flush()
        await self.db.refresh(route)
        return route

    @transactional
    async def update(
        self, route_id: UUID, tenant_id: UUID, data: SEORouteUpdate
    ) -> SEORoute:
        """Update SEO route."""
        route = await self.get_by_id(route_id, tenant_id)
        route.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(route, field, value)

        await self.db.flush()
        await self.db.refresh(route)
        return route

    @transactional
    async def delete(self, route_id: UUID, tenant_id: UUID) -> None:
        """Delete SEO route."""
        route = await self.get_by_id(route_id, tenant_id)
        await self.db.delete(route)
        await self.db.flush()


class RedirectService:
    """Service for managing redirects."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_source(
        self, source_path: str, tenant_id: UUID
    ) -> Redirect | None:
        """Get active redirect by source path."""
        stmt = (
            select(Redirect)
            .where(Redirect.tenant_id == tenant_id)
            .where(Redirect.source_path == source_path)
            .where(Redirect.deleted_at.is_(None))
            .where(Redirect.is_active.is_(True))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, redirect_id: UUID, tenant_id: UUID) -> Redirect:
        """Get redirect by ID."""
        stmt = (
            select(Redirect)
            .where(Redirect.id == redirect_id)
            .where(Redirect.tenant_id == tenant_id)
            .where(Redirect.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        redirect = result.scalar_one_or_none()

        if not redirect:
            raise NotFoundError("Redirect", redirect_id)

        return redirect

    async def list_redirects(
        self,
        tenant_id: UUID,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Redirect], int]:
        """List redirects."""
        base_query = (
            select(Redirect)
            .where(Redirect.tenant_id == tenant_id)
            .where(Redirect.deleted_at.is_(None))
        )

        if is_active is not None:
            base_query = base_query.where(Redirect.is_active == is_active)

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.order_by(Redirect.source_path)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        redirects = list(result.scalars().all())

        return redirects, total

    @transactional
    async def create(self, tenant_id: UUID, data: RedirectCreate) -> Redirect:
        """Create a new redirect."""
        # Check for existing redirect
        existing = await self.get_by_source(data.source_path, tenant_id)
        if existing:
            raise AlreadyExistsError("Redirect", "source_path", data.source_path)

        redirect = Redirect(tenant_id=tenant_id, **data.model_dump())
        self.db.add(redirect)
        await self.db.flush()
        await self.db.refresh(redirect)
        return redirect

    @transactional
    async def update(
        self, redirect_id: UUID, tenant_id: UUID, data: RedirectUpdate
    ) -> Redirect:
        """Update redirect."""
        redirect = await self.get_by_id(redirect_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(redirect, field, value)

        await self.db.flush()
        await self.db.refresh(redirect)
        return redirect

    @transactional
    async def soft_delete(self, redirect_id: UUID, tenant_id: UUID) -> None:
        """Soft delete redirect."""
        redirect = await self.get_by_id(redirect_id, tenant_id)
        redirect.soft_delete()
        await self.db.flush()

    @transactional
    async def record_hit(self, redirect_id: UUID, tenant_id: UUID) -> None:
        """Record a redirect hit."""
        redirect = await self.get_by_id(redirect_id, tenant_id)
        redirect.increment_hit()
        await self.db.flush()

    async def list_active_for_export(
        self, tenant_id: UUID
    ) -> tuple[list[Redirect], datetime | None]:
        """List all active redirects for export to edge/proxy.
        
        Returns:
            Tuple of (redirects list, max updated_at for ETag)
        """
        # Get redirects
        stmt = (
            select(Redirect)
            .where(Redirect.tenant_id == tenant_id)
            .where(Redirect.deleted_at.is_(None))
            .where(Redirect.is_active.is_(True))
            .order_by(Redirect.source_path)
        )
        result = await self.db.execute(stmt)
        redirects = list(result.scalars().all())
        
        # Get max updated_at for ETag
        max_stmt = (
            select(func.max(Redirect.updated_at))
            .where(Redirect.tenant_id == tenant_id)
            .where(Redirect.deleted_at.is_(None))
            .where(Redirect.is_active.is_(True))
        )
        max_result = await self.db.execute(max_stmt)
        max_updated_at = max_result.scalar_one_or_none()
        
        return redirects, max_updated_at

    async def get_redirects_metadata(self, tenant_id: UUID) -> tuple[datetime | None, int]:
        """Get redirects metadata for caching.
        
        Returns:
            Tuple of (max_updated_at, total_count)
        """
        stmt = (
            select(
                func.max(Redirect.updated_at).label("last_modified"),
                func.count().label("total_count"),
            )
            .where(Redirect.tenant_id == tenant_id)
            .where(Redirect.deleted_at.is_(None))
            .where(Redirect.is_active.is_(True))
        )
        result = await self.db.execute(stmt)
        row = result.one()
        return row.last_modified, row.total_count or 0


class SitemapService:
    """Service for generating sitemaps.
    
    This service now delegates to SitemapAggregatorService for full
    sitemap generation including all content sources.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.seo_service = SEORouteService(db)
        # Import here to avoid circular imports
        from app.modules.seo.sitemap_service import SitemapAggregatorService
        self.aggregator = SitemapAggregatorService(db)

    async def get_sitemap_metadata(
        self, tenant_id: UUID, locale: str
    ) -> SitemapMetadata:
        """Get sitemap metadata for caching.
        
        Uses aggregator to get metadata from all content sources.
        """
        agg_metadata = await self.aggregator.get_sitemap_metadata(tenant_id, locale)
        
        # Generate semantic ETag
        ts = int(agg_metadata.last_modified.timestamp()) if agg_metadata.last_modified else 0
        etag = f'W/"sitemap:{tenant_id}:{locale}:{ts}:{agg_metadata.total_count}"'
        
        return SitemapMetadata(
            last_modified=agg_metadata.last_modified,
            total_count=agg_metadata.total_count,
            etag=etag,
        )

    async def generate_sitemap_xml(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> str:
        """Generate sitemap.xml content with all content sources.
        
        Uses SitemapAggregatorService to collect URLs from:
        - Static pages
        - SEO routes
        - Articles, Cases, Services, Topics, Employees, Documents
        """
        urls = await self.aggregator.get_all_sitemap_urls(
            tenant_id=tenant_id,
            locale=locale,
            base_url=base_url,
        )
        return self.aggregator.generate_sitemap_xml(urls)

    async def generate_segment_sitemap_xml(
        self, tenant_id: UUID, locale: str, base_url: str, segment: str
    ) -> str:
        """Generate sitemap XML for a specific segment.
        
        Args:
            segment: One of 'pages', 'articles', 'cases', 'services', 'team', 'documents'
        """
        urls = await self.aggregator.get_urls_by_segment(
            tenant_id=tenant_id,
            locale=locale,
            base_url=base_url,
            segment=segment,
        )
        return self.aggregator.generate_sitemap_xml(urls)

    def generate_sitemap_index_xml(
        self, base_url: str, tenant_id: UUID, locales: list[str]
    ) -> str:
        """Generate sitemap index XML.
        
        Creates an index referencing segment sitemaps for each locale.
        """
        segments = ["pages", "articles", "cases", "services"]
        return self.aggregator.generate_sitemap_index_xml(
            base_url=base_url,
            tenant_id=tenant_id,
            segments=segments,
            locales=locales,
        )

    def generate_robots_txt(
        self,
        base_url: str,
        sitemap_url: str,
        custom_rules: str | None = None,
    ) -> str:
        """Generate robots.txt content.
        
        Args:
            base_url: The base URL for the site
            sitemap_url: URL to the sitemap
            custom_rules: Optional custom rules to append
        """
        content = f"""User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /_next/

Sitemap: {sitemap_url}
"""
        if custom_rules:
            content += f"\n{custom_rules}"
        
        return content

