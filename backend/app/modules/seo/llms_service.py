"""llms.txt generation service for AI discovery.

llms.txt is a curated markdown file that helps AI systems (like LLMs)
understand the structure and content of a website for better citations
and references to primary sources.

Specification: https://llmstxt.org/
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.url_utils import build_sitemap_url
from app.modules.company.models import Service, ServiceLocale
from app.modules.content.models import Case, CaseLocale
from app.modules.tenants.models import Tenant, TenantSettings


class LlmsTxtService:
    """Service for generating llms.txt for AI discovery.
    
    llms.txt provides a curated "high-signal map" of a website,
    not a full sitemap. It includes:
    - Company information
    - Key services (top 5)
    - Featured cases/proof (top 3)
    - Contact information
    """
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def is_enabled(self, tenant_id: UUID) -> bool:
        """Check if llms.txt is enabled for tenant."""
        settings = await self._get_tenant_settings(tenant_id)
        if not settings:
            return False
        return settings.llms_txt_enabled
    
    async def generate(
        self,
        tenant_id: UUID,
        locale: str,
        base_url: str,
    ) -> str:
        """Generate llms.txt content.
        
        Args:
            tenant_id: Tenant ID
            locale: Locale code (e.g., 'ru', 'en')
            base_url: Base URL for the site
            
        Returns:
            Markdown content for llms.txt
        """
        tenant = await self._get_tenant(tenant_id)
        settings = await self._get_tenant_settings(tenant_id)
        
        if not tenant:
            return "# Not Found\n\nTenant not found."
        
        # Build sections
        sections = []
        
        # Header
        sections.append(self._generate_header(tenant, base_url))
        
        # Custom content (if configured)
        if settings and settings.llms_txt_custom_content:
            sections.append(settings.llms_txt_custom_content)
        
        # Services
        services_section = await self._generate_services_section(
            tenant_id, locale, base_url
        )
        if services_section:
            sections.append(services_section)
        
        # Cases/Portfolio
        cases_section = await self._generate_cases_section(
            tenant_id, locale, base_url
        )
        if cases_section:
            sections.append(cases_section)
        
        # Contact
        sections.append(self._generate_contact_section(tenant, base_url))
        
        return "\n\n".join(sections)
    
    def _generate_header(self, tenant: Tenant, base_url: str) -> str:
        """Generate header section."""
        lines = [
            f"# {tenant.name}",
            "",
            f"> Website: {base_url}",
        ]
        
        if tenant.contact_email:
            lines.append(f"> Contact: {tenant.contact_email}")
        
        lines.extend([
            "",
            "## About",
            "",
            f"This is the official website of {tenant.name}.",
        ])
        
        return "\n".join(lines)
    
    async def _generate_services_section(
        self,
        tenant_id: UUID,
        locale: str,
        base_url: str,
    ) -> str | None:
        """Generate services section (top 5)."""
        stmt = (
            select(Service, ServiceLocale)
            .join(ServiceLocale, Service.id == ServiceLocale.service_id)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
            .where(Service.is_published.is_(True))
            .where(ServiceLocale.locale == locale)
            .order_by(Service.sort_order)
            .limit(5)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        if not rows:
            return None
        
        lines = [
            "## Services",
            "",
        ]
        
        for service, locale_data in rows:
            url = build_sitemap_url(base_url, f"/services/{locale_data.slug}")
            name = locale_data.name or service.name
            lines.append(f"- [{name}]({url})")
            
            # Add brief description if available
            if locale_data.meta_description:
                # Truncate to first sentence
                desc = locale_data.meta_description.split(".")[0]
                if desc:
                    lines.append(f"  {desc}.")
        
        return "\n".join(lines)
    
    async def _generate_cases_section(
        self,
        tenant_id: UUID,
        locale: str,
        base_url: str,
    ) -> str | None:
        """Generate cases/portfolio section (top 3)."""
        stmt = (
            select(Case, CaseLocale)
            .join(CaseLocale, Case.id == CaseLocale.case_id)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == "published")
            .where(CaseLocale.locale == locale)
            .order_by(Case.published_at.desc().nullslast())
            .limit(3)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        if not rows:
            return None
        
        lines = [
            "## Portfolio",
            "",
            "Featured case studies demonstrating our work:",
            "",
        ]
        
        for case, locale_data in rows:
            url = build_sitemap_url(base_url, f"/portfolio/{locale_data.slug}")
            title = locale_data.title or case.title
            lines.append(f"- [{title}]({url})")
        
        return "\n".join(lines)
    
    def _generate_contact_section(self, tenant: Tenant, base_url: str) -> str:
        """Generate contact section."""
        lines = [
            "## Contact",
            "",
            f"For inquiries, visit our [contact page]({base_url}/contact).",
        ]
        
        if tenant.contact_email:
            lines.append(f"Email: {tenant.contact_email}")
        
        if tenant.contact_phone:
            lines.append(f"Phone: {tenant.contact_phone}")
        
        return "\n".join(lines)
    
    async def _get_tenant(self, tenant_id: UUID) -> Tenant | None:
        """Get tenant by ID."""
        result = await self.db.execute(
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .where(Tenant.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()
    
    async def _get_tenant_settings(self, tenant_id: UUID) -> TenantSettings | None:
        """Get tenant settings."""
        result = await self.db.execute(
            select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()
