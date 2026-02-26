"""Add slug fields to parameters/values, create parameter_categories,
update product_characteristics constraints for faceted filtering,
drop product_chars (EAV).

Revision ID: 035
Revises: 034
Create Date: 2026-02-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. Add slug to parameters ---
    op.add_column("parameters", sa.Column("slug", sa.String(255), nullable=True))
    op.execute(
        "UPDATE parameters SET slug = LOWER(REPLACE(REPLACE(name, ' ', '-'), '.', '-')) "
        "WHERE slug IS NULL"
    )
    op.alter_column("parameters", "slug", nullable=False)
    op.create_unique_constraint("uq_parameters_tenant_slug", "parameters", ["tenant_id", "slug"])
    op.create_index("ix_parameters_slug", "parameters", ["slug"])

    # --- 2. Add slug to parameter_values ---
    op.add_column("parameter_values", sa.Column("slug", sa.String(255), nullable=True))
    op.execute(
        "UPDATE parameter_values SET slug = LOWER(REPLACE(REPLACE(label, ' ', '-'), '.', '-')) "
        "WHERE slug IS NULL"
    )
    op.alter_column("parameter_values", "slug", nullable=False)
    op.create_unique_constraint("uq_parameter_values_slug", "parameter_values", ["parameter_id", "slug"])

    # --- 3. Create parameter_categories ---
    op.create_table(
        "parameter_categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parameter_id", UUID(as_uuid=True), sa.ForeignKey("parameters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("parameter_id", "category_id", name="uq_parameter_categories"),
    )
    op.create_index("ix_parameter_categories_parameter", "parameter_categories", ["parameter_id"])
    op.create_index("ix_parameter_categories_category", "parameter_categories", ["category_id"])

    # --- 4. Update product_characteristics constraints ---
    op.drop_constraint("uq_product_characteristics_product_param", "product_characteristics", type_="unique")
    op.create_index(
        "uq_prod_chars_enum",
        "product_characteristics",
        ["product_id", "parameter_id", "parameter_value_id"],
        unique=True,
        postgresql_where=sa.text("parameter_value_id IS NOT NULL"),
    )
    op.create_index(
        "uq_prod_chars_scalar",
        "product_characteristics",
        ["product_id", "parameter_id"],
        unique=True,
        postgresql_where=sa.text("parameter_value_id IS NULL"),
    )
    op.create_index(
        "ix_product_characteristics_filter",
        "product_characteristics",
        ["parameter_id", "parameter_value_id"],
    )

    # --- 5. Drop product_chars (EAV) ---
    op.drop_table("product_chars")


def downgrade() -> None:
    # Re-create product_chars
    op.create_table(
        "product_chars",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value_text", sa.Text, nullable=False),
        sa.Column("uom_id", UUID(as_uuid=True), sa.ForeignKey("uoms.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_product_chars_product", "product_chars", ["product_id"])
    op.create_index("ix_product_chars_name", "product_chars", ["name"])

    # Restore old constraint
    op.drop_index("ix_product_characteristics_filter", table_name="product_characteristics")
    op.drop_index("uq_prod_chars_scalar", table_name="product_characteristics")
    op.drop_index("uq_prod_chars_enum", table_name="product_characteristics")
    op.create_unique_constraint(
        "uq_product_characteristics_product_param",
        "product_characteristics",
        ["product_id", "parameter_id"],
    )

    op.drop_table("parameter_categories")

    op.drop_index("ix_parameters_slug", table_name="parameters")
    op.drop_constraint("uq_parameters_tenant_slug", "parameters", type_="unique")
    op.drop_column("parameters", "slug")

    op.drop_constraint("uq_parameter_values_slug", "parameter_values", type_="unique")
    op.drop_column("parameter_values", "slug")
