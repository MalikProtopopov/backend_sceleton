"""SEO module service layer."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.seo.models import Redirect, SEORoute
from app.modules.seo.schemas import RedirectCreate, RedirectUpdate, SEORouteCreate, SEORouteUpdate


class SEORouteService:
    """Service for managing SEO routes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_path(
        self, path: str, locale: str, tenant_id: UUID
    ) -> SEORoute | None:
        """Get SEO route by path and locale."""
        stmt = (
            select(SEORoute)
            .where(SEORoute.tenant_id == tenant_id)
            .where(SEORoute.path == path)
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

    @transactional
    async def create_or_update(
        self, tenant_id: UUID, data: SEORouteCreate
    ) -> SEORoute:
        """Create or update SEO route for a path."""
        existing = await self.get_by_path(data.path, data.locale, tenant_id)

        if existing:
            # Update existing
            for field, value in data.model_dump().items():
                setattr(existing, field, value)
            route = existing
        else:
            # Create new
            route = SEORoute(tenant_id=tenant_id, **data.model_dump())
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


class SitemapService:
    """Service for generating sitemaps."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.seo_service = SEORouteService(db)

    async def generate_sitemap_xml(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> str:
        """Generate sitemap.xml content."""
        urls = await self.seo_service.get_sitemap_urls(tenant_id, locale)

        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]

        for route in urls:
            url_parts = [f"  <url>", f"    <loc>{base_url}{route.path}</loc>"]

            if route.updated_at:
                url_parts.append(
                    f"    <lastmod>{route.updated_at.strftime('%Y-%m-%d')}</lastmod>"
                )

            if route.sitemap_changefreq:
                url_parts.append(f"    <changefreq>{route.sitemap_changefreq}</changefreq>")

            if route.sitemap_priority is not None:
                url_parts.append(f"    <priority>{route.sitemap_priority:.1f}</priority>")

            url_parts.append("  </url>")
            xml_parts.append("\n".join(url_parts))

        xml_parts.append("</urlset>")

        return "\n".join(xml_parts)

    def generate_robots_txt(self, base_url: str, sitemap_url: str) -> str:
        """Generate robots.txt content."""
        return f"""User-agent: *
Allow: /

Sitemap: {sitemap_url}
"""

