"""Add cancelled status to inquiries.

Revision ID: 014
Revises: 013
Create Date: 2026-01-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'cancelled' status to inquiries constraint."""
    # Drop the old constraint
    op.drop_constraint("ck_inquiries_status", "inquiries", type_="check")
    
    # Create new constraint with 'cancelled' status
    op.create_check_constraint(
        "ck_inquiries_status",
        "inquiries",
        "status IN ('new', 'in_progress', 'contacted', 'completed', 'spam', 'cancelled')",
    )


def downgrade() -> None:
    """Remove 'cancelled' status from inquiries constraint."""
    # Drop the new constraint
    op.drop_constraint("ck_inquiries_status", "inquiries", type_="check")
    
    # Restore old constraint without 'cancelled'
    op.create_check_constraint(
        "ck_inquiries_status",
        "inquiries",
        "status IN ('new', 'in_progress', 'contacted', 'completed', 'spam')",
    )
