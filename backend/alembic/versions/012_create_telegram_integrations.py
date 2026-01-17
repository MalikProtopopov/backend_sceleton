"""Create telegram_integrations table.

Revision ID: 012
Revises: 011
Create Date: 2026-01-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create telegram_integrations table."""
    op.create_table(
        "telegram_integrations",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        # Tenant reference
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Bot configuration
        sa.Column(
            "bot_token_encrypted",
            sa.Text(),
            nullable=False,
            comment="Encrypted Telegram bot token",
        ),
        sa.Column(
            "bot_username",
            sa.String(100),
            nullable=True,
            comment="Bot username without @",
        ),
        # Owner notification
        sa.Column(
            "owner_chat_id",
            sa.BigInteger(),
            nullable=True,
            comment="Chat ID for receiving notifications",
        ),
        # Webhook
        sa.Column(
            "webhook_secret",
            sa.String(64),
            nullable=False,
            comment="Secret for webhook validation",
        ),
        sa.Column(
            "webhook_url",
            sa.String(512),
            nullable=True,
            comment="Current webhook URL",
        ),
        sa.Column(
            "is_webhook_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether webhook is active",
        ),
        # Status
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether integration is enabled",
        ),
        # Welcome message
        sa.Column(
            "welcome_message",
            sa.Text(),
            nullable=True,
            comment="Custom /start message",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
    )
    
    # Indexes
    op.create_index(
        "ix_telegram_integrations_tenant_unique",
        "telegram_integrations",
        ["tenant_id"],
        unique=True,
    )
    op.create_index(
        "ix_telegram_integrations_webhook_secret",
        "telegram_integrations",
        ["webhook_secret"],
    )


def downgrade() -> None:
    """Drop telegram_integrations table."""
    op.drop_index("ix_telegram_integrations_webhook_secret", table_name="telegram_integrations")
    op.drop_index("ix_telegram_integrations_tenant_unique", table_name="telegram_integrations")
    op.drop_table("telegram_integrations")

