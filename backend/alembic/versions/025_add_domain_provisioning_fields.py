"""Add domain provisioning fields to tenant_domains.

Revision ID: 025
Revises: 024
Create Date: 2026-02-24

Adds dns_verified_at, ssl_provisioned_at timestamps and extends
ssl_status CHECK constraint to include 'verifying' state.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_domains",
        sa.Column("dns_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tenant_domains",
        sa.Column("ssl_provisioned_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.drop_constraint("ck_tenant_domains_ssl_status", "tenant_domains", type_="check")
    op.create_check_constraint(
        "ck_tenant_domains_ssl_status",
        "tenant_domains",
        "ssl_status IN ('pending', 'verifying', 'active', 'error')",
    )


def downgrade() -> None:
    # Revert any 'verifying' rows back to 'pending' before restoring constraint
    op.execute("UPDATE tenant_domains SET ssl_status = 'pending' WHERE ssl_status = 'verifying'")

    op.drop_constraint("ck_tenant_domains_ssl_status", "tenant_domains", type_="check")
    op.create_check_constraint(
        "ck_tenant_domains_ssl_status",
        "tenant_domains",
        "ssl_status IN ('pending', 'active', 'error')",
    )

    op.drop_column("tenant_domains", "ssl_provisioned_at")
    op.drop_column("tenant_domains", "dns_verified_at")
