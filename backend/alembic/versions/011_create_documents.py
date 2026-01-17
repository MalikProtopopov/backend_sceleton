"""Create documents tables.

Revision ID: 011
Revises: 010
Create Date: 2026-01-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create documents module tables."""
    
    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column("document_version", sa.String(50), nullable=True, comment="Document version (e.g., '1.0', 'v2.3')"),
        sa.Column("document_date", sa.Date(), nullable=True, comment="Date of the document"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_url", sa.String(500), nullable=True, comment="URL to document file (PDF, etc.)"),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_documents_status"),
    )
    op.create_index("ix_documents_tenant", "documents", ["tenant_id"])
    op.create_index("ix_documents_published", "documents", ["tenant_id", "status"], postgresql_where="deleted_at IS NULL AND status = 'published'")
    op.create_index("ix_documents_date", "documents", ["document_date"])

    # Document locales
    op.create_table(
        "document_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("excerpt", sa.String(500), nullable=True, comment="Short description / summary"),
        sa.Column("full_description", sa.Text(), nullable=True, comment="Full HTML description of the document"),
        sa.Column("meta_title", sa.String(70), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("meta_keywords", sa.String(255), nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("document_id", "locale", name="uq_document_locales"),
        sa.CheckConstraint("char_length(title) >= 1", name="ck_document_locales_title"),
        sa.CheckConstraint("char_length(slug) >= 2", name="ck_document_locales_slug"),
    )
    op.create_index("ix_document_locales_slug", "document_locales", ["locale", "slug"])


def downgrade() -> None:
    """Drop documents tables."""
    op.drop_table("document_locales")
    op.drop_table("documents")

