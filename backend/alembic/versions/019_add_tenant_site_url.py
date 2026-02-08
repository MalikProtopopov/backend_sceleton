"""Add site_url to tenant_settings for sitemap/robots frontend domain.

Revision ID: 019
Revises: 018
Create Date: 2026-02-08

Adds site_url (frontend base URL) so sitemap <loc> and robots.txt Sitemap:
use the frontend domain (e.g. https://mediann.dev) instead of the API request URL.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add site_url column to tenant_settings."""
    op.add_column(
        "tenant_settings",
        sa.Column(
            "site_url",
            sa.String(500),
            nullable=True,
            comment="Frontend base URL for sitemap/robots (e.g. https://mediann.dev). Used in <loc> and Sitemap: directive.",
        ),
    )


def downgrade() -> None:
    """Remove site_url column from tenant_settings."""
    op.drop_column("tenant_settings", "site_url")
