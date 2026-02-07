"""Expand ym_counter_id column from VARCHAR(20) to TEXT.

Revision ID: 018
Revises: 017
Create Date: 2026-02-07

This migration changes ym_counter_id from VARCHAR(20) to TEXT
to support full Yandex.Metrika embed code, not just the counter ID.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change ym_counter_id from VARCHAR(20) to TEXT."""
    op.alter_column(
        "tenant_settings",
        "ym_counter_id",
        existing_type=sa.String(20),
        type_=sa.Text,
        existing_nullable=True,
        comment="Yandex.Metrika counter ID or embed code",
    )


def downgrade() -> None:
    """Revert ym_counter_id back to VARCHAR(20)."""
    op.alter_column(
        "tenant_settings",
        "ym_counter_id",
        existing_type=sa.Text,
        type_=sa.String(20),
        existing_nullable=True,
    )
