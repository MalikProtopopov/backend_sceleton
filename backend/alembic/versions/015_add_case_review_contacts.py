"""Add contacts tables for cases and reviews.

Revision ID: 015
Revises: 014
Create Date: 2026-02-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create contact tables for cases and reviews."""
    
    # Create case_contacts table
    op.create_table(
        "case_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Contact type: website, instagram, telegram, linkedin, facebook, etc.
        sa.Column("contact_type", sa.String(50), nullable=False),
        # Contact value: URL, phone number, email, username, etc.
        sa.Column("value", sa.String(500), nullable=False),
        # Sort order
        sa.Column("sort_order", sa.Integer, default=0, nullable=False),
    )

    # Indexes for case_contacts
    op.create_index("ix_case_contacts_case", "case_contacts", ["case_id"])

    # Create review_author_contacts table
    op.create_table(
        "review_author_contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "review_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Contact type: website, instagram, telegram, linkedin, facebook, etc.
        sa.Column("contact_type", sa.String(50), nullable=False),
        # Contact value: URL, phone number, email, username, etc.
        sa.Column("value", sa.String(500), nullable=False),
        # Sort order
        sa.Column("sort_order", sa.Integer, default=0, nullable=False),
    )

    # Indexes for review_author_contacts
    op.create_index("ix_review_author_contacts_review", "review_author_contacts", ["review_id"])


def downgrade() -> None:
    """Drop contact tables."""
    op.drop_table("review_author_contacts")
    op.drop_table("case_contacts")
