"""Create reviews table.

Revision ID: 010
Revises: 009
Create Date: 2026-01-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create reviews table for social proof / testimonials."""
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        # Moderation status
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        # Rating
        sa.Column("rating", sa.Integer, nullable=False),
        # Author info
        sa.Column("author_name", sa.String(255), nullable=False),
        sa.Column("author_company", sa.String(255), nullable=True),
        sa.Column("author_position", sa.String(255), nullable=True),
        sa.Column("author_photo_url", sa.String(500), nullable=True),
        # Content
        sa.Column("content", sa.Text, nullable=False),
        # Case link
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Features
        sa.Column("is_featured", sa.Boolean, default=False, nullable=False),
        # Source
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        # Review date
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        # Sort order
        sa.Column("sort_order", sa.Integer, default=0, nullable=False),
        # Version for optimistic locking
        sa.Column("version", sa.Integer, default=1, nullable=False),
        # Soft delete
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_reviews_tenant", "reviews", ["tenant_id"])
    op.create_index("ix_reviews_status", "reviews", ["tenant_id", "status"])
    op.create_index(
        "ix_reviews_approved",
        "reviews",
        ["tenant_id", "status"],
        postgresql_where="deleted_at IS NULL AND status = 'approved'",
    )
    op.create_index("ix_reviews_featured", "reviews", ["tenant_id", "is_featured"])
    op.create_index("ix_reviews_case", "reviews", ["case_id"])
    op.create_index("ix_reviews_deleted_at", "reviews", ["deleted_at"])

    # Check constraints
    op.create_check_constraint(
        "ck_reviews_rating_range",
        "reviews",
        "rating >= 1 AND rating <= 5",
    )
    op.create_check_constraint(
        "ck_reviews_status",
        "reviews",
        "status IN ('pending', 'approved', 'rejected')",
    )
    op.create_check_constraint(
        "ck_reviews_author_name",
        "reviews",
        "char_length(author_name) >= 2",
    )
    op.create_check_constraint(
        "ck_reviews_content_min",
        "reviews",
        "char_length(content) >= 10",
    )


def downgrade() -> None:
    """Drop reviews table."""
    op.drop_table("reviews")


