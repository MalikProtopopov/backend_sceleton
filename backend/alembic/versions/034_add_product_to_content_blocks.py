"""Allow 'product' as entity_type in content_blocks.

Revision ID: 034
Revises: 033
Create Date: 2026-02-24
"""

from typing import Sequence, Union

from alembic import op

revision: str = "034"
down_revision: Union[str, None] = "033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old CHECK constraint and recreate with 'product' added
    op.drop_constraint(
        "ck_content_blocks_entity_type",
        "content_blocks",
        type_="check",
    )
    op.create_check_constraint(
        "ck_content_blocks_entity_type",
        "content_blocks",
        "entity_type IN ('article', 'case', 'service', 'employee', 'product')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_content_blocks_entity_type",
        "content_blocks",
        type_="check",
    )
    op.create_check_constraint(
        "ck_content_blocks_entity_type",
        "content_blocks",
        "entity_type IN ('article', 'case', 'service', 'employee')",
    )
