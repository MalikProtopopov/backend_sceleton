"""Create parameter tables: parameters, parameter_values,
product_chars, product_characteristics.

Revision ID: 031
Revises: 030
Create Date: 2026-02-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- parameters --
    op.create_table(
        "parameters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value_type", sa.String(20), nullable=False),
        sa.Column("uom_id", UUID(as_uuid=True), sa.ForeignKey("uoms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scope", sa.String(20), nullable=False, server_default="global"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("constraints", JSONB, nullable=True),
        sa.Column("is_filterable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "value_type IN ('string', 'number', 'enum', 'bool', 'range')",
            name="ck_parameters_value_type",
        ),
        sa.CheckConstraint(
            "scope IN ('global', 'category')",
            name="ck_parameters_scope",
        ),
    )
    op.create_index("ix_parameters_tenant", "parameters", ["tenant_id"])
    op.create_index("ix_parameters_name", "parameters", ["name"])
    op.create_index("ix_parameters_active", "parameters", ["tenant_id", "is_active"])

    # -- parameter_values --
    op.create_table(
        "parameter_values",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parameter_id", UUID(as_uuid=True), sa.ForeignKey("parameters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("code", sa.String(100), nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("parameter_id", "label", name="uq_parameter_values_label"),
    )
    op.create_index("ix_parameter_values_parameter", "parameter_values", ["parameter_id"])

    # -- product_chars (EAV) --
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

    # -- product_characteristics (normalized) --
    op.create_table(
        "product_characteristics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_id", UUID(as_uuid=True), sa.ForeignKey("parameters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parameter_value_id", UUID(as_uuid=True), sa.ForeignKey("parameter_values.id", ondelete="SET NULL"), nullable=True),
        sa.Column("value_text", sa.Text, nullable=True),
        sa.Column("value_number", sa.Numeric, nullable=True),
        sa.Column("value_bool", sa.Boolean, nullable=True),
        sa.Column("uom_id", UUID(as_uuid=True), sa.ForeignKey("uoms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("is_locked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("product_id", "parameter_id", name="uq_product_characteristics_product_param"),
        sa.CheckConstraint(
            "source_type IN ('manual', 'import', 'system')",
            name="ck_product_characteristics_source",
        ),
    )
    op.create_index("ix_product_characteristics_product", "product_characteristics", ["product_id"])
    op.create_index("ix_product_characteristics_parameter", "product_characteristics", ["parameter_id"])


def downgrade() -> None:
    op.drop_table("product_characteristics")
    op.drop_table("product_chars")
    op.drop_table("parameter_values")
    op.drop_table("parameters")
