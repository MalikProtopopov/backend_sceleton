"""Add per-tenant email/SMTP settings and email_logs table.

Revision ID: 023
Revises: 022
Create Date: 2026-02-13

Adds email/SMTP configuration columns to tenant_settings and
creates email_logs table for tracking all email send attempts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email/SMTP columns to tenant_settings and create email_logs table."""
    # --- tenant_settings: email/SMTP columns ---
    op.add_column(
        "tenant_settings",
        sa.Column(
            "email_provider",
            sa.String(20),
            nullable=True,
            comment="Email provider: smtp, sendgrid, mailgun, console. NULL = use global default",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "email_from_address",
            sa.String(255),
            nullable=True,
            comment="Sender email address for this tenant",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "email_from_name",
            sa.String(255),
            nullable=True,
            comment="Sender display name for this tenant",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "smtp_host",
            sa.String(255),
            nullable=True,
            comment="SMTP server host (e.g. smtp.gmail.com)",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "smtp_port",
            sa.Integer(),
            nullable=True,
            server_default="587",
            comment="SMTP server port (587=STARTTLS, 465=SSL)",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "smtp_user",
            sa.String(255),
            nullable=True,
            comment="SMTP authentication username",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "smtp_password_encrypted",
            sa.Text(),
            nullable=True,
            comment="SMTP password (encrypted with Fernet)",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "smtp_use_tls",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Use STARTTLS for SMTP connection",
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "email_api_key_encrypted",
            sa.Text(),
            nullable=True,
            comment="SendGrid/Mailgun API key (encrypted with Fernet)",
        ),
    )

    # Check constraint for email_provider values
    op.create_check_constraint(
        "ck_tenant_settings_email_provider",
        "tenant_settings",
        "email_provider IS NULL OR email_provider IN ('smtp', 'sendgrid', 'mailgun', 'console')",
    )

    # --- email_logs table ---
    op.create_table(
        "email_logs",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column(
            "email_type",
            sa.String(50),
            nullable=False,
            comment="welcome, password_reset, inquiry, test",
        ),
        sa.Column(
            "provider",
            sa.String(20),
            nullable=False,
            comment="smtp, sendgrid, mailgun, console",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            comment="sent, failed, console",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_email_logs_tenant_created", "email_logs", ["tenant_id", "created_at"])
    op.create_index("ix_email_logs_status", "email_logs", ["status"])


def downgrade() -> None:
    """Remove email/SMTP columns and email_logs table."""
    op.drop_index("ix_email_logs_status", table_name="email_logs")
    op.drop_index("ix_email_logs_tenant_created", table_name="email_logs")
    op.drop_table("email_logs")

    op.drop_constraint("ck_tenant_settings_email_provider", "tenant_settings", type_="check")

    op.drop_column("tenant_settings", "email_api_key_encrypted")
    op.drop_column("tenant_settings", "smtp_use_tls")
    op.drop_column("tenant_settings", "smtp_password_encrypted")
    op.drop_column("tenant_settings", "smtp_user")
    op.drop_column("tenant_settings", "smtp_port")
    op.drop_column("tenant_settings", "smtp_host")
    op.drop_column("tenant_settings", "email_from_name")
    op.drop_column("tenant_settings", "email_from_address")
    op.drop_column("tenant_settings", "email_provider")
