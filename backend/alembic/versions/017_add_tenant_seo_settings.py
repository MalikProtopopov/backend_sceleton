"""Add SEO settings to tenant_settings table.

Revision ID: 017
Revises: 016
Create Date: 2026-02-03

This migration adds SEO-related fields to the tenant_settings table:
- allowed_domains: List of allowed domains for sitemap/robots validation
- sitemap_static_pages: Static pages configuration for sitemap
- robots_txt_custom_rules: Custom rules to append to robots.txt
- indexnow_key: IndexNow API key
- indexnow_enabled: Enable IndexNow URL submission
- llms_txt_enabled: Enable llms.txt generation
- llms_txt_custom_content: Custom content for llms.txt
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add SEO settings columns to tenant_settings."""
    
    # SEO domain validation
    op.add_column(
        "tenant_settings",
        sa.Column(
            "allowed_domains",
            JSONB,
            nullable=True,
            comment="List of allowed domains for sitemap/robots base_url validation",
        ),
    )
    
    # Sitemap configuration
    op.add_column(
        "tenant_settings",
        sa.Column(
            "sitemap_static_pages",
            JSONB,
            nullable=True,
            comment="Static pages for sitemap [{path, priority, changefreq}]",
        ),
    )
    
    # Robots.txt customization
    op.add_column(
        "tenant_settings",
        sa.Column(
            "robots_txt_custom_rules",
            sa.Text,
            nullable=True,
            comment="Custom rules to append to robots.txt",
        ),
    )
    
    # IndexNow integration
    op.add_column(
        "tenant_settings",
        sa.Column(
            "indexnow_key",
            sa.String(64),
            nullable=True,
            comment="IndexNow API key for search engine notification",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "indexnow_enabled",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="Enable IndexNow URL submission",
        ),
    )
    
    # AI discovery (llms.txt)
    op.add_column(
        "tenant_settings",
        sa.Column(
            "llms_txt_enabled",
            sa.Boolean,
            nullable=False,
            server_default="false",
            comment="Enable llms.txt generation for AI discovery",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "llms_txt_custom_content",
            sa.Text,
            nullable=True,
            comment="Custom content to include in llms.txt",
        ),
    )


def downgrade() -> None:
    """Remove SEO settings columns from tenant_settings."""
    
    op.drop_column("tenant_settings", "llms_txt_custom_content")
    op.drop_column("tenant_settings", "llms_txt_enabled")
    op.drop_column("tenant_settings", "indexnow_enabled")
    op.drop_column("tenant_settings", "indexnow_key")
    op.drop_column("tenant_settings", "robots_txt_custom_rules")
    op.drop_column("tenant_settings", "sitemap_static_pages")
    op.drop_column("tenant_settings", "allowed_domains")
