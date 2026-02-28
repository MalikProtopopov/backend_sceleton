"""Add product variants system: product_type/has_variants/price_from/price_to
on products, plus new tables for option groups, option values, variants,
variant prices, variant option links, variant inclusions, variant images.

Revision ID: 036
Revises: 035
Create Date: 2026-02-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = "036"
down_revision: Union[str, None] = "035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Extend products table
    # ------------------------------------------------------------------
    op.add_column(
        "products",
        sa.Column("product_type", sa.String(20), nullable=False, server_default="physical"),
    )
    op.add_column(
        "products",
        sa.Column("has_variants", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "products",
        sa.Column("price_from", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("price_to", sa.Numeric(18, 2), nullable=True),
    )

    op.create_check_constraint(
        "ck_products_product_type",
        "products",
        "product_type IN ('physical', 'digital', 'service', 'course', 'subscription')",
    )
    op.create_index(
        "ix_products_product_type",
        "products",
        ["product_type"],
    )
    op.create_index(
        "ix_products_price_from",
        "products",
        ["tenant_id", "price_from"],
        postgresql_where="deleted_at IS NULL AND is_active = true",
    )

    # Populate price_from/price_to from existing regular prices
    op.execute("""
        UPDATE products p
        SET price_from = sub.min_price,
            price_to   = sub.max_price
        FROM (
            SELECT product_id,
                   MIN(amount) AS min_price,
                   MAX(amount) AS max_price
            FROM product_prices
            WHERE price_type = 'regular'
              AND (valid_from IS NULL OR valid_from <= CURRENT_DATE)
              AND (valid_to   IS NULL OR valid_to   >= CURRENT_DATE)
            GROUP BY product_id
        ) sub
        WHERE p.id = sub.product_id
    """)

    # ------------------------------------------------------------------
    # 2. product_option_groups
    # ------------------------------------------------------------------
    op.create_table(
        "product_option_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("display_type", sa.String(20), nullable=False, server_default="dropdown"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("parameter_id", UUID(as_uuid=True), sa.ForeignKey("parameters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_option_groups_product_slug", "product_option_groups", ["product_id", "slug"])
    op.create_check_constraint(
        "ck_option_groups_display_type",
        "product_option_groups",
        "display_type IN ('dropdown', 'buttons', 'color_swatch', 'cards')",
    )
    op.create_index("ix_option_groups_product", "product_option_groups", ["product_id"])

    # ------------------------------------------------------------------
    # 3. product_option_values
    # ------------------------------------------------------------------
    op.create_table(
        "product_option_values",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("option_group_id", UUID(as_uuid=True), sa.ForeignKey("product_option_groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color_hex", sa.String(7), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_option_values_group_slug", "product_option_values", ["option_group_id", "slug"])
    op.create_index("ix_option_values_group", "product_option_values", ["option_group_id"])

    # ------------------------------------------------------------------
    # 4. product_variants
    # ------------------------------------------------------------------
    op.create_table(
        "product_variants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_quantity", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Numeric(10, 3), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_variants_tenant_sku", "product_variants", ["tenant_id", "sku"])
    op.create_unique_constraint("uq_variants_product_slug", "product_variants", ["product_id", "slug"])
    op.create_index(
        "ix_variants_product_active", "product_variants", ["product_id"],
        postgresql_where="deleted_at IS NULL",
    )
    op.create_index("ix_variants_tenant_active", "product_variants", ["tenant_id", "is_active"])

    # ------------------------------------------------------------------
    # 5. variant_prices
    # ------------------------------------------------------------------
    op.create_table(
        "variant_prices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price_type", sa.String(20), nullable=False, server_default="regular"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_check_constraint("ck_variant_prices_type", "variant_prices", "price_type IN ('regular', 'sale', 'wholesale', 'cost')")
    op.create_check_constraint("ck_variant_prices_amount_positive", "variant_prices", "amount >= 0")
    op.create_index("ix_variant_prices_variant", "variant_prices", ["variant_id"])
    op.create_index("ix_variant_prices_valid", "variant_prices", ["variant_id", "price_type", "valid_from"])

    # ------------------------------------------------------------------
    # 6. variant_option_links
    # ------------------------------------------------------------------
    op.create_table(
        "variant_option_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("option_value_id", UUID(as_uuid=True), sa.ForeignKey("product_option_values.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_unique_constraint("uq_variant_option_links", "variant_option_links", ["variant_id", "option_value_id"])
    op.create_index("ix_variant_option_links_variant", "variant_option_links", ["variant_id"])
    op.create_index("ix_variant_option_links_value", "variant_option_links", ["option_value_id"])

    # ------------------------------------------------------------------
    # 7. variant_inclusions
    # ------------------------------------------------------------------
    op.create_table(
        "variant_inclusions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_included", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("group", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_variant_inclusions_variant", "variant_inclusions", ["variant_id"])

    # ------------------------------------------------------------------
    # 8. variant_images
    # ------------------------------------------------------------------
    op.create_table(
        "variant_images",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("variant_id", UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("alt", sa.String(500), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(50), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("is_cover", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_variant_images_variant", "variant_images", ["variant_id"])
    op.create_index("ix_variant_images_cover", "variant_images", ["variant_id", "is_cover"])

    # Add variants_module feature flag for all existing tenants (disabled by default)
    op.execute("""
        INSERT INTO feature_flags (id, tenant_id, feature_name, enabled, description)
        SELECT gen_random_uuid(), id, 'variants_module', false,
               'Product variants, tariff plans, option groups'
        FROM tenants
        WHERE id NOT IN (
            SELECT tenant_id FROM feature_flags WHERE feature_name = 'variants_module'
        )
    """)


def downgrade() -> None:
    op.execute("DELETE FROM feature_flags WHERE feature_name = 'variants_module'")

    op.drop_table("variant_images")
    op.drop_table("variant_inclusions")
    op.drop_table("variant_option_links")
    op.drop_table("variant_prices")
    op.drop_table("product_variants")
    op.drop_table("product_option_values")
    op.drop_table("product_option_groups")

    op.drop_index("ix_products_price_from", table_name="products")
    op.drop_index("ix_products_product_type", table_name="products")
    op.drop_constraint("ck_products_product_type", "products", type_="check")
    op.drop_column("products", "price_to")
    op.drop_column("products", "price_from")
    op.drop_column("products", "has_variants")
    op.drop_column("products", "product_type")
