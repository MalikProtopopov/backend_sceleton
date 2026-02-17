"""Add webmaster verification fields to tenant_settings.

Revision ID: 025
Revises: 024
Create Date: 2026-02-16

Adds yandex_verification_code, google_verification_code, and
google_verification_meta columns to tenant_settings for site ownership
verification via Yandex.Webmaster and Google Search Console.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_settings",
        sa.Column(
            "yandex_verification_code",
            sa.String(255),
            nullable=True,
            comment="Yandex.Webmaster verification filename without .html (e.g. yandex_821edd51f146c052)",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "google_verification_code",
            sa.String(255),
            nullable=True,
            comment="Google Search Console verification filename without .html (e.g. google1234567890abcdef)",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "google_verification_meta",
            sa.String(500),
            nullable=True,
            comment="Google Search Console meta tag content attribute value (alternative to file)",
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_settings", "google_verification_meta")
    op.drop_column("tenant_settings", "google_verification_code")
    op.drop_column("tenant_settings", "yandex_verification_code")
