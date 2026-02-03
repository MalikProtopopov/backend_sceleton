"""Sitemap aggregation service for collecting URLs from all content sources."""

from datetime import datetime
from uuid import UUID
from xml.sax.saxutils import escape as xml_escape

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.url_utils import build_sitemap_url, normalize_path
from app.modules.company.models import Employee, EmployeeLocale, Service, ServiceLocale
from app.modules.content.models import Article, ArticleLocale, Case, CaseLocale, Topic, TopicLocale
from app.modules.documents.models import Document, DocumentLocale
from app.modules.seo.models import SEORoute
from app.modules.tenants.models import TenantSettings


# Default static pages for sitemap
DEFAULT_STATIC_PAGES = [
    {"path": "/", "priority": 1.0, "changefreq": "weekly"},
    {"path": "/services", "priority": 0.9, "changefreq": "weekly"},
    {"path": "/portfolio", "priority": 0.9, "changefreq": "weekly"},
    {"path": "/blog", "priority": 0.8, "changefreq": "daily"},
    {"path": "/about", "priority": 0.7, "changefreq": "monthly"},
    {"path": "/team", "priority": 0.7, "changefreq": "monthly"},
    {"path": "/contact", "priority": 0.6, "changefreq": "monthly"},
    {"path": "/faq", "priority": 0.6, "changefreq": "monthly"},
]


class SitemapURL:
    """Represents a URL entry for sitemap."""
    
    def __init__(
        self,
        loc: str,
        lastmod: datetime | None = None,
        changefreq: str | None = "weekly",
        priority: float | None = 0.5,
        segment: str = "pages",
    ):
        self.loc = loc
        self.lastmod = lastmod
        self.changefreq = changefreq
        self.priority = priority
        self.segment = segment  # For sitemap index segmentation


class SitemapMetadata:
    """Metadata for sitemap caching."""
    
    def __init__(
        self,
        last_modified: datetime | None = None,
        total_count: int = 0,
        segment_counts: dict[str, int] | None = None,
    ):
        self.last_modified = last_modified
        self.total_count = total_count
        self.segment_counts = segment_counts or {}


class SitemapAggregatorService:
    """Service for aggregating sitemap URLs from all content sources."""
    
    # URL patterns for different content types
    URL_PATTERNS = {
        "articles": "/blog/{slug}",
        "topics": "/blog/topic/{slug}",
        "cases": "/portfolio/{slug}",
        "services": "/services/{slug}",
        "employees": "/team/{slug}",
        "documents": "/documents/{slug}",
    }
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def get_all_sitemap_urls(
        self,
        tenant_id: UUID,
        locale: str,
        base_url: str,
        include_static: bool = True,
    ) -> list[SitemapURL]:
        """Get all URLs for sitemap from all sources.
        
        Sources:
        1. Static pages (from config or TenantSettings)
        2. SEORoute entries (manual pages/landings)
        3. Published articles
        4. Published cases
        5. Published services
        6. Topics with articles
        7. Published employees (if team pages exist)
        8. Published documents
        
        Exclusions:
        - Unpublished/draft content
        - Soft-deleted content
        - SEORoute with robots_index=False
        - Pages with canonical_url pointing elsewhere
        """
        urls: list[SitemapURL] = []
        
        # 1. Static pages
        if include_static:
            static_urls = await self._get_static_pages(tenant_id, base_url)
            urls.extend(static_urls)
        
        # 2. SEO Routes (manual pages)
        seo_urls = await self._get_seo_routes(tenant_id, locale, base_url)
        urls.extend(seo_urls)
        
        # 3. Articles
        article_urls = await self._get_articles(tenant_id, locale, base_url)
        urls.extend(article_urls)
        
        # 4. Cases
        case_urls = await self._get_cases(tenant_id, locale, base_url)
        urls.extend(case_urls)
        
        # 5. Services
        service_urls = await self._get_services(tenant_id, locale, base_url)
        urls.extend(service_urls)
        
        # 6. Topics
        topic_urls = await self._get_topics(tenant_id, locale, base_url)
        urls.extend(topic_urls)
        
        # 7. Employees
        employee_urls = await self._get_employees(tenant_id, locale, base_url)
        urls.extend(employee_urls)
        
        # 8. Documents
        document_urls = await self._get_documents(tenant_id, locale, base_url)
        urls.extend(document_urls)
        
        return urls
    
    async def get_urls_by_segment(
        self,
        tenant_id: UUID,
        locale: str,
        base_url: str,
        segment: str,
    ) -> list[SitemapURL]:
        """Get URLs for a specific sitemap segment.
        
        Args:
            segment: One of 'pages', 'articles', 'cases', 'services'
        """
        if segment == "pages":
            urls = await self._get_static_pages(tenant_id, base_url)
            urls.extend(await self._get_seo_routes(tenant_id, locale, base_url))
            return urls
        elif segment == "articles":
            urls = await self._get_articles(tenant_id, locale, base_url)
            urls.extend(await self._get_topics(tenant_id, locale, base_url))
            return urls
        elif segment == "cases":
            return await self._get_cases(tenant_id, locale, base_url)
        elif segment == "services":
            return await self._get_services(tenant_id, locale, base_url)
        elif segment == "team":
            return await self._get_employees(tenant_id, locale, base_url)
        elif segment == "documents":
            return await self._get_documents(tenant_id, locale, base_url)
        else:
            return []
    
    async def get_sitemap_metadata(
        self,
        tenant_id: UUID,
        locale: str,
    ) -> SitemapMetadata:
        """Get metadata for sitemap caching (last_modified, counts).
        
        Queries max(updated_at) across all included entities.
        """
        max_dates: list[datetime | None] = []
        segment_counts: dict[str, int] = {}
        
        # SEO Routes
        seo_result = await self.db.execute(
            select(
                func.max(SEORoute.updated_at),
                func.count(),
            )
            .where(SEORoute.tenant_id == tenant_id)
            .where(SEORoute.locale == locale)
            .where(SEORoute.include_in_sitemap.is_(True))
            .where(SEORoute.robots_index.is_(True))
        )
        seo_row = seo_result.one()
        max_dates.append(seo_row[0])
        segment_counts["pages"] = seo_row[1] or 0
        
        # Articles
        article_result = await self.db.execute(
            select(
                func.max(Article.updated_at),
                func.count(),
            )
            .select_from(Article)
            .join(ArticleLocale, Article.id == ArticleLocale.article_id)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
            .where(Article.status == "published")
            .where(ArticleLocale.locale == locale)
        )
        article_row = article_result.one()
        max_dates.append(article_row[0])
        segment_counts["articles"] = article_row[1] or 0
        
        # Cases
        case_result = await self.db.execute(
            select(
                func.max(Case.updated_at),
                func.count(),
            )
            .select_from(Case)
            .join(CaseLocale, Case.id == CaseLocale.case_id)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == "published")
            .where(CaseLocale.locale == locale)
        )
        case_row = case_result.one()
        max_dates.append(case_row[0])
        segment_counts["cases"] = case_row[1] or 0
        
        # Services
        service_result = await self.db.execute(
            select(
                func.max(Service.updated_at),
                func.count(),
            )
            .select_from(Service)
            .join(ServiceLocale, Service.id == ServiceLocale.service_id)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
            .where(Service.is_published.is_(True))
            .where(ServiceLocale.locale == locale)
        )
        service_row = service_result.one()
        max_dates.append(service_row[0])
        segment_counts["services"] = service_row[1] or 0
        
        # Calculate overall max and total
        valid_dates = [d for d in max_dates if d is not None]
        last_modified = max(valid_dates) if valid_dates else None
        total_count = sum(segment_counts.values())
        
        # Add static pages count
        settings = await self._get_tenant_settings(tenant_id)
        static_pages = settings.sitemap_static_pages if settings else None
        if not static_pages:
            static_pages = DEFAULT_STATIC_PAGES
        segment_counts["pages"] += len(static_pages)
        total_count += len(static_pages)
        
        return SitemapMetadata(
            last_modified=last_modified,
            total_count=total_count,
            segment_counts=segment_counts,
        )
    
    async def _get_tenant_settings(self, tenant_id: UUID) -> TenantSettings | None:
        """Get tenant settings."""
        result = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_static_pages(
        self, tenant_id: UUID, base_url: str
    ) -> list[SitemapURL]:
        """Get static pages from tenant settings or defaults."""
        settings = await self._get_tenant_settings(tenant_id)
        static_pages = None
        if settings:
            static_pages = settings.sitemap_static_pages
        
        if not static_pages:
            static_pages = DEFAULT_STATIC_PAGES
        
        urls = []
        for page in static_pages:
            path = page.get("path", "/")
            full_url = build_sitemap_url(base_url, path)
            urls.append(SitemapURL(
                loc=full_url,
                priority=page.get("priority", 0.5),
                changefreq=page.get("changefreq", "weekly"),
                segment="pages",
            ))
        
        return urls
    
    async def _get_seo_routes(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> list[SitemapURL]:
        """Get SEO routes (manual pages/landings)."""
        stmt = (
            select(SEORoute)
            .where(SEORoute.tenant_id == tenant_id)
            .where(SEORoute.locale == locale)
            .where(SEORoute.include_in_sitemap.is_(True))
            .where(SEORoute.robots_index.is_(True))
            # Exclude pages with canonical pointing elsewhere
            .where(
                (SEORoute.canonical_url.is_(None)) | 
                (SEORoute.canonical_url == "")
            )
            .order_by(SEORoute.sitemap_priority.desc().nullslast())
        )
        result = await self.db.execute(stmt)
        routes = result.scalars().all()
        
        urls = []
        for route in routes:
            full_url = build_sitemap_url(base_url, route.path)
            urls.append(SitemapURL(
                loc=full_url,
                lastmod=route.updated_at,
                priority=route.sitemap_priority,
                changefreq=route.sitemap_changefreq,
                segment="pages",
            ))
        
        return urls
    
    async def _get_articles(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> list[SitemapURL]:
        """Get published articles."""
        stmt = (
            select(Article, ArticleLocale)
            .join(ArticleLocale, Article.id == ArticleLocale.article_id)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
            .where(Article.status == "published")
            .where(ArticleLocale.locale == locale)
            .order_by(Article.published_at.desc().nullslast())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        urls = []
        for article, locale_data in rows:
            path = self.URL_PATTERNS["articles"].format(slug=locale_data.slug)
            full_url = build_sitemap_url(base_url, path)
            urls.append(SitemapURL(
                loc=full_url,
                lastmod=article.updated_at,
                priority=0.7,
                changefreq="weekly",
                segment="articles",
            ))
        
        return urls
    
    async def _get_cases(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> list[SitemapURL]:
        """Get published cases."""
        stmt = (
            select(Case, CaseLocale)
            .join(CaseLocale, Case.id == CaseLocale.case_id)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == "published")
            .where(CaseLocale.locale == locale)
            .order_by(Case.published_at.desc().nullslast())
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        urls = []
        for case, locale_data in rows:
            path = self.URL_PATTERNS["cases"].format(slug=locale_data.slug)
            full_url = build_sitemap_url(base_url, path)
            urls.append(SitemapURL(
                loc=full_url,
                lastmod=case.updated_at,
                priority=0.7,
                changefreq="monthly",
                segment="cases",
            ))
        
        return urls
    
    async def _get_services(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> list[SitemapURL]:
        """Get published services."""
        stmt = (
            select(Service, ServiceLocale)
            .join(ServiceLocale, Service.id == ServiceLocale.service_id)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
            .where(Service.is_published.is_(True))
            .where(ServiceLocale.locale == locale)
            .order_by(Service.sort_order)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        urls = []
        for service, locale_data in rows:
            path = self.URL_PATTERNS["services"].format(slug=locale_data.slug)
            full_url = build_sitemap_url(base_url, path)
            urls.append(SitemapURL(
                loc=full_url,
                lastmod=service.updated_at,
                priority=0.8,
                changefreq="weekly",
                segment="services",
            ))
        
        return urls
    
    async def _get_topics(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> list[SitemapURL]:
        """Get topics (blog categories)."""
        stmt = (
            select(Topic, TopicLocale)
            .join(TopicLocale, Topic.id == TopicLocale.topic_id)
            .where(Topic.tenant_id == tenant_id)
            .where(Topic.deleted_at.is_(None))
            .where(TopicLocale.locale == locale)
            .order_by(Topic.sort_order)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        urls = []
        for topic, locale_data in rows:
            path = self.URL_PATTERNS["topics"].format(slug=locale_data.slug)
            full_url = build_sitemap_url(base_url, path)
            urls.append(SitemapURL(
                loc=full_url,
                lastmod=topic.updated_at,
                priority=0.6,
                changefreq="weekly",
                segment="articles",  # Group with articles
            ))
        
        return urls
    
    async def _get_employees(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> list[SitemapURL]:
        """Get published employees (team members)."""
        stmt = (
            select(Employee, EmployeeLocale)
            .join(EmployeeLocale, Employee.id == EmployeeLocale.employee_id)
            .where(Employee.tenant_id == tenant_id)
            .where(Employee.deleted_at.is_(None))
            .where(Employee.is_published.is_(True))
            .where(EmployeeLocale.locale == locale)
            .order_by(Employee.sort_order)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        urls = []
        for employee, locale_data in rows:
            path = self.URL_PATTERNS["employees"].format(slug=locale_data.slug)
            full_url = build_sitemap_url(base_url, path)
            urls.append(SitemapURL(
                loc=full_url,
                lastmod=employee.updated_at,
                priority=0.5,
                changefreq="monthly",
                segment="team",
            ))
        
        return urls
    
    async def _get_documents(
        self, tenant_id: UUID, locale: str, base_url: str
    ) -> list[SitemapURL]:
        """Get published documents."""
        stmt = (
            select(Document, DocumentLocale)
            .join(DocumentLocale, Document.id == DocumentLocale.document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
            .where(Document.status == "published")
            .where(DocumentLocale.locale == locale)
            .order_by(Document.sort_order)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        urls = []
        for document, locale_data in rows:
            path = self.URL_PATTERNS["documents"].format(slug=locale_data.slug)
            full_url = build_sitemap_url(base_url, path)
            urls.append(SitemapURL(
                loc=full_url,
                lastmod=document.updated_at,
                priority=0.4,
                changefreq="monthly",
                segment="documents",
            ))
        
        return urls
    
    def generate_sitemap_xml(self, urls: list[SitemapURL]) -> str:
        """Generate sitemap XML from URL list.
        
        Uses XML escaping for safe URL encoding.
        """
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        
        for url in urls:
            escaped_url = xml_escape(url.loc)
            url_parts = ["  <url>", f"    <loc>{escaped_url}</loc>"]
            
            if url.lastmod:
                url_parts.append(
                    f"    <lastmod>{url.lastmod.strftime('%Y-%m-%d')}</lastmod>"
                )
            
            if url.changefreq:
                url_parts.append(f"    <changefreq>{xml_escape(url.changefreq)}</changefreq>")
            
            if url.priority is not None:
                url_parts.append(f"    <priority>{url.priority:.1f}</priority>")
            
            url_parts.append("  </url>")
            xml_parts.append("\n".join(url_parts))
        
        xml_parts.append("</urlset>")
        return "\n".join(xml_parts)
    
    def generate_sitemap_index_xml(
        self,
        base_url: str,
        tenant_id: UUID,
        segments: list[str],
        locales: list[str],
    ) -> str:
        """Generate sitemap index XML referencing segment sitemaps.
        
        Args:
            base_url: Base URL for the site
            tenant_id: Tenant ID
            segments: List of segment names (e.g., ['pages', 'articles', 'cases'])
            locales: List of locale codes (e.g., ['ru', 'en'])
        """
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        
        api_base = f"{base_url}/api/v1/public"
        
        for locale in locales:
            for segment in segments:
                sitemap_url = f"{api_base}/sitemap-{segment}-{locale}.xml?tenant_id={tenant_id}"
                escaped_url = xml_escape(sitemap_url)
                xml_parts.append(f"""  <sitemap>
    <loc>{escaped_url}</loc>
  </sitemap>""")
        
        xml_parts.append("</sitemapindex>")
        return "\n".join(xml_parts)
