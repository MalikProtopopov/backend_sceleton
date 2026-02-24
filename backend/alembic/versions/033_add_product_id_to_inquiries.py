"""Add product_id to inquiries table.

Revision ID: 033
Revises: 032
Create Date: 2026-02-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID

revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "inquiries",
        sa.Column("product_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_inquiries_product_id",
        "inquiries", "products",
        ["product_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_inquiries_product", "inquiries", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_inquiries_product", table_name="inquiries")
    op.drop_constraint("fk_inquiries_product_id", "inquiries", type_="foreignkey")
    op.drop_column("inquiries", "product_id")
