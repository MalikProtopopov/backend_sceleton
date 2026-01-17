"""Create tenants tables.

Revision ID: 001
Revises: 
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tenants, tenant_settings, and feature_flags tables."""
    # Tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("domain", sa.String(255), nullable=True, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(slug) >= 2", name="ck_tenants_slug_min_length"),
        sa.CheckConstraint(
            "primary_color IS NULL OR primary_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_tenants_primary_color_format",
        ),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_active", "tenants", ["is_active"], postgresql_where="deleted_at IS NULL")

    # Tenant settings table
    op.create_table(
        "tenant_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("default_locale", sa.String(5), nullable=False, default="ru"),
        sa.Column("timezone", sa.String(50), nullable=False, default="Europe/Moscow"),
        sa.Column("date_format", sa.String(20), nullable=False, default="DD.MM.YYYY"),
        sa.Column("time_format", sa.String(10), nullable=False, default="HH:mm"),
        sa.Column("notify_on_inquiry", sa.Boolean(), nullable=False, default=True),
        sa.Column("inquiry_email", sa.String(255), nullable=True),
        sa.Column("telegram_chat_id", sa.String(50), nullable=True),
        sa.Column("default_og_image", sa.String(500), nullable=True),
        sa.Column("ga_tracking_id", sa.String(50), nullable=True),
        sa.Column("ym_counter_id", sa.String(20), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint(
            "default_locale ~ '^[a-z]{2}(-[A-Z]{2})?$'",
            name="ck_tenant_settings_locale_format",
        ),
    )
    op.create_index("ix_tenant_settings_tenant", "tenant_settings", ["tenant_id"])

    # Feature flags table
    op.create_table(
        "feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_name", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.CheckConstraint(
            "feature_name ~ '^[a-z][a-z0-9_]*$'",
            name="ck_feature_flags_name_format",
        ),
    )
    op.create_index("ix_feature_flags_tenant_feature", "feature_flags", ["tenant_id", "feature_name"], unique=True)
    op.create_index("ix_feature_flags_enabled", "feature_flags", ["tenant_id", "enabled"], postgresql_where="enabled = true")


def downgrade() -> None:
    """Drop tenants tables."""
    op.drop_table("feature_flags")
    op.drop_table("tenant_settings")
    op.drop_table("tenants")

