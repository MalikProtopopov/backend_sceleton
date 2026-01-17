"""Create SEO tables.

Revision ID: 007
Revises: 006
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create SEO module tables."""
    
    # SEO routes table
    op.create_table(
        "seo_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(70), nullable=True),
        sa.Column("meta_title", sa.String(70), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("meta_keywords", sa.String(255), nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("canonical_url", sa.String(500), nullable=True),
        sa.Column("robots_index", sa.Boolean(), nullable=False, default=True),
        sa.Column("robots_follow", sa.Boolean(), nullable=False, default=True),
        sa.Column("structured_data", sa.Text(), nullable=True),
        sa.Column("sitemap_priority", sa.Float(), nullable=True, default=0.5),
        sa.Column("sitemap_changefreq", sa.String(20), nullable=True, default="weekly"),
        sa.Column("include_in_sitemap", sa.Boolean(), nullable=False, default=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint("sitemap_priority IS NULL OR (sitemap_priority >= 0 AND sitemap_priority <= 1)", name="ck_seo_routes_priority_range"),
        sa.CheckConstraint("sitemap_changefreq IS NULL OR sitemap_changefreq IN ('always', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'never')", name="ck_seo_routes_changefreq"),
    )
    op.create_index("ix_seo_routes_tenant_path", "seo_routes", ["tenant_id", "path", "locale"], unique=True)

    # Redirects table
    op.create_table(
        "redirects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("target_url", sa.String(2000), nullable=False),
        sa.Column("redirect_type", sa.Integer(), nullable=False, default=301),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("redirect_type IN (301, 302, 307, 308)", name="ck_redirects_type"),
        sa.CheckConstraint("char_length(source_path) >= 1", name="ck_redirects_source_path"),
    )
    op.create_index("ix_redirects_tenant_source", "redirects", ["tenant_id", "source_path"], unique=True)
    op.create_index("ix_redirects_active", "redirects", ["tenant_id"], postgresql_where="deleted_at IS NULL AND is_active = true")


def downgrade() -> None:
    """Drop SEO tables."""
    op.drop_table("redirects")
    op.drop_table("seo_routes")

