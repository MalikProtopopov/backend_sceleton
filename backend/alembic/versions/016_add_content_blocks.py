"""Add content_blocks table for flexible content system.

Revision ID: 016
Revises: 015
Create Date: 2026-02-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create content_blocks table for flexible content system."""
    
    op.create_table(
        "content_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        # Polymorphic relationship
        sa.Column(
            "entity_type",
            sa.String(20),
            nullable=False,
            comment="Entity type: article, case, service",
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="ID of the related entity",
        ),
        sa.Column(
            "locale",
            sa.String(5),
            nullable=False,
            comment="Locale code: ru, en, etc.",
        ),
        # Block type
        sa.Column(
            "block_type",
            sa.String(30),
            nullable=False,
            comment="Block type: text, image, video, gallery, link, result",
        ),
        # Sort order
        sa.Column("sort_order", sa.Integer, default=0, nullable=False),
        # Content fields
        sa.Column(
            "title",
            sa.String(255),
            nullable=True,
            comment="Optional block title/heading",
        ),
        sa.Column(
            "content",
            sa.Text,
            nullable=True,
            comment="HTML content for text blocks",
        ),
        sa.Column(
            "media_url",
            sa.String(500),
            nullable=True,
            comment="URL for image or video",
        ),
        sa.Column(
            "thumbnail_url",
            sa.String(500),
            nullable=True,
            comment="Thumbnail URL for video blocks",
        ),
        sa.Column(
            "link_url",
            sa.String(500),
            nullable=True,
            comment="Link URL for link/result blocks",
        ),
        sa.Column(
            "link_label",
            sa.String(255),
            nullable=True,
            comment="Link button text",
        ),
        sa.Column(
            "device_type",
            sa.String(10),
            nullable=True,
            default="both",
            comment="Device type: mobile, desktop, both",
        ),
        sa.Column(
            "block_metadata",
            postgresql.JSONB,
            nullable=True,
            comment="Additional metadata (alt, caption, images[], provider, icon)",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Indexes
    op.create_index("ix_content_blocks_tenant", "content_blocks", ["tenant_id"])
    op.create_index(
        "ix_content_blocks_entity",
        "content_blocks",
        ["entity_type", "entity_id", "locale"],
    )
    op.create_index(
        "ix_content_blocks_entity_sorted",
        "content_blocks",
        ["entity_type", "entity_id", "locale", "sort_order"],
    )

    # Check constraints
    op.create_check_constraint(
        "ck_content_blocks_entity_type",
        "content_blocks",
        "entity_type IN ('article', 'case', 'service')",
    )
    op.create_check_constraint(
        "ck_content_blocks_block_type",
        "content_blocks",
        "block_type IN ('text', 'image', 'video', 'gallery', 'link', 'result')",
    )
    op.create_check_constraint(
        "ck_content_blocks_device_type",
        "content_blocks",
        "device_type IS NULL OR device_type IN ('mobile', 'desktop', 'both')",
    )


def downgrade() -> None:
    """Drop content_blocks table."""
    op.drop_table("content_blocks")
