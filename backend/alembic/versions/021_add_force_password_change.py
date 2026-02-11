"""Add force_password_change column to admin_users.

Revision ID: 021
Revises: 020
Create Date: 2026-02-11

Adds force_password_change boolean column to admin_users table.
New users get force_password_change=True by default.
Existing users get force_password_change=False.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add force_password_change column with default false for existing users."""
    op.add_column(
        "admin_users",
        sa.Column(
            "force_password_change",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Remove force_password_change column."""
    op.drop_column("admin_users", "force_password_change")
