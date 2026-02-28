"""Phase 3: FK constraints, partial unique indexes, CHECK constraints.

Revision ID: 037
Revises: 036
Create Date: 2026-02-26
"""

from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None

_TENANT_MIXIN_TABLES = [
    "products",
    "product_prices",
    "product_images",
    "product_aliases",
    "categories",
    "product_categories",
    "product_option_groups",
    "product_variants",
    "parameters",
    "parameter_values",
    "product_characteristics",
    "employees",
    "employee_locales",
    "cases",
    "case_contacts",
    "case_locales",
    "reviews",
    "review_author_contacts",
    "review_locales",
    "articles",
    "article_locales",
    "article_topics",
    "topics",
    "topic_locales",
    "documents",
    "document_locales",
    "inquiries",
    "inquiry_forms",
    "content_blocks",
    "content_block_locales",
    "faq_items",
    "faq_item_locales",
    "telegram_integrations",
    "file_assets",
    "seo_routes",
]


def upgrade() -> None:
    # 3.1 — Add FK constraint on tenant_id (skip gracefully on any schema mismatch)
    for table in _TENANT_MIXIN_TABLES:
        fk_name = f"fk_{table}_tenant_id"
        op.execute(f"""
            DO $$ BEGIN
                ALTER TABLE {table}
                    ADD CONSTRAINT {fk_name}
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
                WHEN undefined_table THEN NULL;
                WHEN undefined_column THEN NULL;
            END $$;
        """)

    # 3.2 — Partial unique indexes (soft-delete safe)
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS uq_products_tenant_sku")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS uq_products_tenant_slug")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_products_tenant_sku
        ON products (tenant_id, sku) WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_products_tenant_slug
        ON products (tenant_id, slug) WHERE deleted_at IS NULL
    """)

    op.execute("ALTER TABLE categories DROP CONSTRAINT IF EXISTS uq_categories_tenant_slug")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_categories_tenant_slug
        ON categories (tenant_id, slug) WHERE deleted_at IS NULL
    """)

    op.execute("ALTER TABLE product_variants DROP CONSTRAINT IF EXISTS uq_variants_tenant_sku")
    op.execute("ALTER TABLE product_variants DROP CONSTRAINT IF EXISTS uq_variants_product_slug")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_variants_tenant_sku
        ON product_variants (tenant_id, sku) WHERE deleted_at IS NULL
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_variants_product_slug
        ON product_variants (product_id, slug) WHERE deleted_at IS NULL
    """)

    # 3.4 — CHECK constraints (skip if already exists)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE product_prices
                ADD CONSTRAINT chk_product_prices_currency CHECK (length(currency) = 3);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE variant_prices
                ADD CONSTRAINT chk_variant_prices_currency CHECK (length(currency) = 3);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE variant_prices DROP CONSTRAINT IF EXISTS chk_variant_prices_currency")
    op.execute("ALTER TABLE product_prices DROP CONSTRAINT IF EXISTS chk_product_prices_currency")

    op.execute("DROP INDEX IF EXISTS uq_variants_product_slug")
    op.execute("DROP INDEX IF EXISTS uq_variants_tenant_sku")
    op.execute("DROP INDEX IF EXISTS uq_categories_tenant_slug")
    op.execute("DROP INDEX IF EXISTS uq_products_tenant_slug")
    op.execute("DROP INDEX IF EXISTS uq_products_tenant_sku")

    for table in reversed(_TENANT_MIXIN_TABLES):
        fk_name = f"fk_{table}_tenant_id"
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {fk_name}")
