"""Create tenant_domains table for multi-domain tenant resolution.

Revision ID: 024
Revises: 023
Create Date: 2026-02-13

Adds tenant_domains table to support mapping multiple custom domains
(e.g. admin.client.com) to tenants. Optionally migrates existing
Tenant.domain values into the new table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tenant_domains table ---
    op.create_table(
        "tenant_domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(255), nullable=False, unique=True, comment="Fully-qualified domain name, e.g. admin.client.com"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="Primary domain shown in tenant switcher links"),
        sa.Column("ssl_status", sa.String(20), nullable=False, server_default=sa.text("'pending'"), comment="SSL certificate status: pending, active, error"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("ix_tenant_domains_tenant_id", "tenant_domains", ["tenant_id"])
    op.create_index("ix_tenant_domains_domain", "tenant_domains", ["domain"], unique=True)

    op.create_check_constraint(
        "ck_tenant_domains_ssl_status",
        "tenant_domains",
        "ssl_status IN ('pending', 'active', 'error')",
    )
    op.create_check_constraint(
        "ck_tenant_domains_domain_min_length",
        "tenant_domains",
        "char_length(domain) >= 4",
    )

    # --- Migrate existing Tenant.domain values (if any) ---
    op.execute("""
        INSERT INTO tenant_domains (id, tenant_id, domain, is_primary, ssl_status, created_at, updated_at)
        SELECT gen_random_uuid(), id, domain, true, 'active', now(), now()
        FROM tenants
        WHERE domain IS NOT NULL AND char_length(domain) >= 4 AND deleted_at IS NULL
    """)


def downgrade() -> None:
    op.drop_table("tenant_domains")
