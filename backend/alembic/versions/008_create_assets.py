"""Create assets tables.

Revision ID: 008
Revises: 007
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create assets module tables."""
    
    # File assets table
    op.create_table(
        "file_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("s3_bucket", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("s3_url", sa.String(1000), nullable=False),
        sa.Column("cdn_url", sa.String(1000), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("alt_text", sa.String(500), nullable=True),
        sa.Column("folder", sa.String(100), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("file_size > 0", name="ck_file_assets_size_positive"),
    )
    op.create_index("ix_file_assets_tenant", "file_assets", ["tenant_id"])
    op.create_index("ix_file_assets_folder", "file_assets", ["tenant_id", "folder"])
    op.create_index("ix_file_assets_s3_key", "file_assets", ["s3_key"], unique=True)


def downgrade() -> None:
    """Drop assets tables."""
    op.drop_table("file_assets")

