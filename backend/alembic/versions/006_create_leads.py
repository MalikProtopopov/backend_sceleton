"""Create leads tables.

Revision ID: 006
Revises: 005
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create leads module tables."""
    
    # Inquiry forms table
    op.create_table(
        "inquiry_forms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("notification_email", sa.String(255), nullable=True),
        sa.Column("success_message", postgresql.JSONB(), nullable=True),
        sa.Column("fields_config", postgresql.JSONB(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(slug) >= 2", name="ck_inquiry_forms_slug_min"),
    )
    op.create_index("ix_inquiry_forms_tenant", "inquiry_forms", ["tenant_id"])
    op.create_index("ix_inquiry_forms_slug", "inquiry_forms", ["tenant_id", "slug"], unique=True)

    # Inquiries table (with full analytics fields)
    op.create_table(
        "inquiries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("inquiry_forms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="new"),
        # Contact info
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        # Service context
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True),
        # UTM tracking
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_medium", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("utm_term", sa.String(255), nullable=True),
        sa.Column("utm_content", sa.String(255), nullable=True),
        # Referrer
        sa.Column("referrer_url", sa.String(2000), nullable=True),
        # Page context
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("page_path", sa.String(500), nullable=True),
        sa.Column("page_title", sa.String(500), nullable=True),
        # Device & browser
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("browser", sa.String(100), nullable=True),
        sa.Column("os", sa.String(100), nullable=True),
        sa.Column("screen_resolution", sa.String(20), nullable=True),
        # Location
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        # Session
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("session_page_views", sa.Integer(), nullable=True),
        sa.Column("time_on_page", sa.Integer(), nullable=True),
        # Custom data
        sa.Column("custom_fields", postgresql.JSONB(), nullable=True),
        # Processing
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, default=False),
        sa.Column("notification_sent_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.CheckConstraint("status IN ('new', 'in_progress', 'contacted', 'completed', 'spam')", name="ck_inquiries_status"),
        sa.CheckConstraint("device_type IS NULL OR device_type IN ('desktop', 'mobile', 'tablet', 'other')", name="ck_inquiries_device_type"),
    )
    # Indexes
    op.create_index("ix_inquiries_tenant", "inquiries", ["tenant_id"])
    op.create_index("ix_inquiries_status", "inquiries", ["tenant_id", "status"])
    op.create_index("ix_inquiries_created", "inquiries", ["tenant_id", "created_at"])
    op.create_index("ix_inquiries_form", "inquiries", ["form_id"])
    op.create_index("ix_inquiries_service", "inquiries", ["service_id"])
    op.create_index("ix_inquiries_assigned", "inquiries", ["assigned_to"])
    # Analytics indexes
    op.create_index("ix_inquiries_utm_source", "inquiries", ["tenant_id", "utm_source"])
    op.create_index("ix_inquiries_utm_campaign", "inquiries", ["tenant_id", "utm_campaign"])
    op.create_index("ix_inquiries_device", "inquiries", ["tenant_id", "device_type"])


def downgrade() -> None:
    """Drop leads tables."""
    op.drop_table("inquiries")
    op.drop_table("inquiry_forms")

