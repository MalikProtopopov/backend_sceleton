"""Add service_prices and service_tags tables.

Revision ID: 013
Revises: 012
Create Date: 2026-01-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create service_prices and service_tags tables."""
    
    # Service prices table
    op.create_table(
        "service_prices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "locale",
            sa.String(5),
            nullable=False,
            comment="Locale code (e.g., 'ru', 'en')",
        ),
        sa.Column(
            "price",
            sa.Numeric(12, 2),
            nullable=False,
            comment="Price value",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            default="RUB",
            comment="Currency code (RUB, USD)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "price >= 0",
            name="ck_service_prices_price_positive",
        ),
        sa.CheckConstraint(
            "currency IN ('RUB', 'USD')",
            name="ck_service_prices_currency",
        ),
        sa.UniqueConstraint(
            "service_id",
            "locale",
            "currency",
            name="uq_service_prices_locale_currency",
        ),
    )
    op.create_index(
        "ix_service_prices_service_id",
        "service_prices",
        ["service_id"],
    )
    op.create_index(
        "ix_service_prices_locale",
        "service_prices",
        ["service_id", "locale"],
    )
    
    # Service tags table
    op.create_table(
        "service_tags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "locale",
            sa.String(5),
            nullable=False,
            comment="Locale code (e.g., 'ru', 'en')",
        ),
        sa.Column(
            "tag",
            sa.String(100),
            nullable=False,
            comment="Tag name",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.CheckConstraint(
            "char_length(tag) >= 1",
            name="ck_service_tags_tag_length",
        ),
        sa.UniqueConstraint(
            "service_id",
            "locale",
            "tag",
            name="uq_service_tags_locale_tag",
        ),
    )
    op.create_index(
        "ix_service_tags_service_id",
        "service_tags",
        ["service_id"],
    )
    op.create_index(
        "ix_service_tags_locale",
        "service_tags",
        ["service_id", "locale"],
    )


def downgrade() -> None:
    """Drop service_prices and service_tags tables."""
    op.drop_table("service_tags")
    op.drop_table("service_prices")

