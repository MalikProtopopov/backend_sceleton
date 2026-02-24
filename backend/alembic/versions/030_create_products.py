"""Create product tables: products, product_images, product_aliases,
product_analogs, product_categories, product_prices.

Revision ID: 030
Revises: 029
Create Date: 2026-02-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- products --
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("brand", sa.String(255), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("uom_id", UUID(as_uuid=True), sa.ForeignKey("uoms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
    )
    op.create_index("ix_products_tenant", "products", ["tenant_id"])
    op.create_index("ix_products_title", "products", ["title"])
    op.create_index("ix_products_brand", "products", ["brand"])
    op.create_index("ix_products_uom", "products", ["uom_id"])
    op.create_index(
        "ix_products_active", "products", ["tenant_id", "is_active"],
        postgresql_where=sa.text("deleted_at IS NULL AND is_active = true"),
    )

    # -- product_images --
    op.create_table(
        "product_images",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("alt", sa.String(500), nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("mime_type", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("is_cover", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_product_images_product", "product_images", ["product_id"])
    op.create_index("ix_product_images_cover", "product_images", ["product_id", "is_cover"])

    # -- product_aliases --
    op.create_table(
        "product_aliases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias", sa.Text, nullable=False),
    )
    op.create_index("ix_product_aliases_product", "product_aliases", ["product_id"])
    op.create_index("ix_product_aliases_alias", "product_aliases", ["alias"])

    # -- product_analogs (composite PK) --
    op.create_table(
        "product_analogs",
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("analog_product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relation", sa.String(20), nullable=False, server_default="equivalent"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.CheckConstraint("relation IN ('equivalent', 'better', 'worse')", name="ck_product_analogs_relation"),
        sa.CheckConstraint("product_id != analog_product_id", name="ck_product_analogs_no_self_ref"),
    )

    # -- product_categories --
    op.create_table(
        "product_categories",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.UniqueConstraint("product_id", "category_id", name="uq_product_categories"),
    )
    op.create_index("ix_product_categories_product", "product_categories", ["product_id"])
    op.create_index("ix_product_categories_category", "product_categories", ["category_id"])

    # -- product_prices --
    op.create_table(
        "product_prices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_type", sa.String(20), nullable=False, server_default="regular"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("valid_from", sa.Date, nullable=True),
        sa.Column("valid_to", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("price_type IN ('regular', 'sale', 'wholesale', 'cost')", name="ck_product_prices_type"),
        sa.CheckConstraint("amount >= 0", name="ck_product_prices_amount_positive"),
    )
    op.create_index("ix_product_prices_product", "product_prices", ["product_id"])
    op.create_index("ix_product_prices_valid", "product_prices", ["product_id", "price_type", "valid_from"])


def downgrade() -> None:
    op.drop_table("product_prices")
    op.drop_table("product_categories")
    op.drop_table("product_analogs")
    op.drop_table("product_aliases")
    op.drop_table("product_images")
    op.drop_table("products")
