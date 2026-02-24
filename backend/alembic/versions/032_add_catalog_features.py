"""Add slug to products, catalog_module feature flag, catalog permissions.

Revision ID: 032
Revises: 031
Create Date: 2026-02-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- slug column on products ---
    op.add_column("products", sa.Column("slug", sa.String(255), nullable=True))
    op.execute(sa.text("UPDATE products SET slug = sku WHERE slug IS NULL"))
    op.alter_column("products", "slug", nullable=False)
    op.create_unique_constraint(
        "uq_products_tenant_slug", "products", ["tenant_id", "slug"]
    )
    op.create_index("ix_products_slug", "products", ["slug"])

    # --- catalog_module feature flag for all existing tenants ---
    op.execute(
        sa.text("""
            INSERT INTO feature_flags (id, tenant_id, feature_name, enabled, description, created_at, updated_at)
            SELECT
                gen_random_uuid(),
                t.id,
                'catalog_module',
                TRUE,
                'Product catalog management',
                NOW(),
                NOW()
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM feature_flags ff
                WHERE ff.tenant_id = t.id AND ff.feature_name = 'catalog_module'
            )
        """)
    )

    # --- catalog permissions ---
    catalog_perms = [
        ("catalog:create", "Create Catalog Items", "catalog", "create"),
        ("catalog:read", "Read Catalog Items", "catalog", "read"),
        ("catalog:update", "Update Catalog Items", "catalog", "update"),
        ("catalog:delete", "Delete Catalog Items", "catalog", "delete"),
    ]
    for code, name, resource, action in catalog_perms:
        op.execute(
            sa.text("""
                INSERT INTO permissions (id, code, name, resource, action, created_at, updated_at)
                SELECT gen_random_uuid(), :code, :name, :resource, :action, NOW(), NOW()
                WHERE NOT EXISTS (
                    SELECT 1 FROM permissions WHERE code = :code
                )
            """),
            {"code": code, "name": name, "resource": resource, "action": action},
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN ('catalog:create', 'catalog:read', 'catalog:update', 'catalog:delete')"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM feature_flags WHERE feature_name = 'catalog_module'"
        )
    )
    op.drop_index("ix_products_slug", table_name="products")
    op.drop_constraint("uq_products_tenant_slug", "products", type_="unique")
    op.drop_column("products", "slug")
