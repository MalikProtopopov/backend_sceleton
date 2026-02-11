"""Add employee to content_blocks entity_type.

Revision ID: 020
Revises: 019
Create Date: 2026-02-08

Allows content blocks to be attached to employees (team members),
same as for articles, cases, and services.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow entity_type 'employee' in content_blocks."""
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


def downgrade() -> None:
    """Revert to article, case, service only."""
    op.drop_constraint(
        "ck_content_blocks_entity_type",
        "content_blocks",
        type_="check",
    )
    op.create_check_constraint(
        "ck_content_blocks_entity_type",
        "content_blocks",
        "entity_type IN ('article', 'case', 'service')",
    )
