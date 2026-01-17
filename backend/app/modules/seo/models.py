"""SEO module database models."""

from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import (
    Base,
    SEOMixin,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


class SEORoute(Base, UUIDMixin, TimestampMixin, TenantMixin, VersionMixin, SEOMixin):
    """SEO metadata for specific routes/pages.

    Allows custom meta tags for any URL path.
    """

    __tablename__ = "seo_routes"

    # URL path (e.g., '/services/consulting', '/about')
    path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Locale
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Page title (can override default)
    title: Mapped[str | None] = mapped_column(String(70), nullable=True)

    # Canonical URL (if different from path)
    canonical_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Robots directives
    robots_index: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    robots_follow: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Structured data (JSON-LD)
    structured_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Priority for sitemap (0.0 to 1.0)
    sitemap_priority: Mapped[float | None] = mapped_column(default=0.5, nullable=True)

    # Change frequency for sitemap
    sitemap_changefreq: Mapped[str | None] = mapped_column(
        String(20), default="weekly", nullable=True
    )

    # Include in sitemap
    include_in_sitemap: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_seo_routes_tenant_path", "tenant_id", "path", "locale", unique=True),
        CheckConstraint(
            "sitemap_priority IS NULL OR (sitemap_priority >= 0 AND sitemap_priority <= 1)",
            name="ck_seo_routes_priority_range",
        ),
        CheckConstraint(
            "sitemap_changefreq IS NULL OR sitemap_changefreq IN ('always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never')",
            name="ck_seo_routes_changefreq",
        ),
    )

    def __repr__(self) -> str:
        return f"<SEORoute {self.path}>"

    @property
    def robots_meta(self) -> str:
        """Generate robots meta content."""
        parts = []
        parts.append("index" if self.robots_index else "noindex")
        parts.append("follow" if self.robots_follow else "nofollow")
        return ", ".join(parts)


class Redirect(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """URL redirects for SEO.

    Manages 301/302 redirects for changed URLs.
    """

    __tablename__ = "redirects"

    # Source path (without domain)
    source_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Target URL (can be path or full URL)
    target_url: Mapped[str] = mapped_column(String(2000), nullable=False)

    # Redirect type
    redirect_type: Mapped[int] = mapped_column(Integer, default=301, nullable=False)

    # Is active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Hit count (for analytics)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_redirects_tenant_source", "tenant_id", "source_path", unique=True),
        Index(
            "ix_redirects_active",
            "tenant_id",
            postgresql_where="deleted_at IS NULL AND is_active = true",
        ),
        CheckConstraint(
            "redirect_type IN (301, 302, 307, 308)",
            name="ck_redirects_type",
        ),
        CheckConstraint(
            "char_length(source_path) >= 1",
            name="ck_redirects_source_path",
        ),
    )

    def __repr__(self) -> str:
        return f"<Redirect {self.source_path} -> {self.target_url}>"

    def increment_hit(self) -> None:
        """Increment hit counter."""
        self.hit_count += 1

