"""Create cases tables.

Revision ID: 009
Revises: 008
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create cases, case_locales, and case_service_links tables."""
    # Cases table
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cover_image_url", sa.String(500), nullable=True),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("project_year", sa.Integer(), nullable=True),
        sa.Column("project_duration", sa.String(100), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=False, default=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_cases_status",
        ),
    )
    op.create_index("ix_cases_tenant", "cases", ["tenant_id"])
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index(
        "ix_cases_published",
        "cases",
        ["tenant_id", "status"],
        postgresql_where="deleted_at IS NULL AND status = 'published'",
    )
    op.create_index("ix_cases_featured", "cases", ["tenant_id", "is_featured"])

    # Case locales table
    op.create_table(
        "case_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("excerpt", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        # SEO fields
        sa.Column("meta_title", sa.String(70), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("meta_keywords", sa.String(255), nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("case_id", "locale", name="uq_case_locales"),
    )
    op.create_index("ix_case_locales_slug", "case_locales", ["locale", "slug"])

    # Case-Service links table
    op.create_table(
        "case_service_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("case_id", "service_id", name="uq_case_service_links"),
    )


def downgrade() -> None:
    """Drop cases tables."""
    op.drop_table("case_service_links")
    op.drop_table("case_locales")
    op.drop_table("cases")

