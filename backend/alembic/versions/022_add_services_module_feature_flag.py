"""Add services_module feature flag to all existing tenants.

Revision ID: 022
Revises: 021
Create Date: 2026-02-11

Adds a 'services_module' feature flag (enabled by default) to every
existing tenant so that the new require_services guard does not
break access for tenants created before this migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert services_module feature flag for all existing tenants."""
    # Use raw SQL to insert the flag for every tenant that doesn't already have it.
    op.execute(
        sa.text("""
            INSERT INTO feature_flags (id, tenant_id, feature_name, enabled, description, created_at, updated_at)
            SELECT
                gen_random_uuid(),
                t.id,
                'services_module',
                TRUE,
                'Manage company services and practice areas',
                NOW(),
                NOW()
            FROM tenants t
            WHERE NOT EXISTS (
                SELECT 1 FROM feature_flags ff
                WHERE ff.tenant_id = t.id AND ff.feature_name = 'services_module'
            )
        """)
    )


def downgrade() -> None:
    """Remove services_module feature flag from all tenants."""
    op.execute(
        sa.text(
            "DELETE FROM feature_flags WHERE feature_name = 'services_module'"
        )
    )
