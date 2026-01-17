"""Create locales configuration table.

Revision ID: 002
Revises: 001
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create locale_configs table."""
    op.create_table(
        "locale_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("native_name", sa.String(50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_rtl", sa.Boolean(), nullable=False, default=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint(
            "locale ~ '^[a-z]{2}(-[A-Z]{2})?$'",
            name="ck_locale_configs_locale_format",
        ),
    )
    op.create_index("ix_locale_configs_tenant_locale", "locale_configs", ["tenant_id", "locale"], unique=True)
    op.create_index("ix_locale_configs_tenant_default", "locale_configs", ["tenant_id"], postgresql_where="is_default = true")
    op.create_index("ix_locale_configs_tenant_enabled", "locale_configs", ["tenant_id", "is_enabled"], postgresql_where="is_enabled = true")


def downgrade() -> None:
    """Drop locale_configs table."""
    op.drop_table("locale_configs")

