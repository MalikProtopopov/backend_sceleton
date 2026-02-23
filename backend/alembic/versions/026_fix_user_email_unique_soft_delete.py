"""Make user email uniqueness respect soft deletes.

Revision ID: 026
Revises: 025
Create Date: 2026-02-23

Replaces the absolute unique constraint on (tenant_id, email) with a
partial unique index that only covers non-deleted rows.  This allows
re-creating a user with the same email after soft-deleting the previous one.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_admin_users_tenant_email", "admin_users", type_="unique")
    op.create_index(
        "uq_admin_users_tenant_email",
        "admin_users",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where="deleted_at IS NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_admin_users_tenant_email", "admin_users")
    op.create_unique_constraint(
        "uq_admin_users_tenant_email", "admin_users", ["tenant_id", "email"]
    )
