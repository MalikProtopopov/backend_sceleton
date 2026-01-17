"""Create company tables.

Revision ID: 004
Revises: 003
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create company module tables."""
    
    # Services table
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("price_from", sa.Integer(), nullable=True),
        sa.Column("price_currency", sa.String(3), nullable=False, default="RUB"),
        sa.Column("is_published", sa.Boolean(), nullable=False, default=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("price_from IS NULL OR price_from >= 0", name="ck_services_price_positive"),
    )
    op.create_index("ix_services_tenant", "services", ["tenant_id"])
    op.create_index("ix_services_published", "services", ["tenant_id", "is_published"], postgresql_where="deleted_at IS NULL AND is_published = true")

    # Service locales
    op.create_table(
        "service_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("services.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("short_description", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(70), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("meta_keywords", sa.String(255), nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("service_id", "locale", name="uq_service_locales"),
        sa.CheckConstraint("char_length(title) >= 1", name="ck_service_locales_title"),
        sa.CheckConstraint("char_length(slug) >= 2", name="ck_service_locales_slug"),
    )
    op.create_index("ix_service_locales_slug", "service_locales", ["locale", "slug"])

    # Practice areas
    op.create_table(
        "practice_areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, default=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_practice_areas_tenant", "practice_areas", ["tenant_id"])
    op.create_index("ix_practice_areas_published", "practice_areas", ["tenant_id", "is_published"], postgresql_where="deleted_at IS NULL AND is_published = true")

    # Practice area locales
    op.create_table(
        "practice_area_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("practice_area_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("practice_areas.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("practice_area_id", "locale", name="uq_practice_area_locales"),
    )
    op.create_index("ix_practice_area_locales_slug", "practice_area_locales", ["locale", "slug"])

    # Employees
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("linkedin_url", sa.String(500), nullable=True),
        sa.Column("telegram_url", sa.String(500), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, default=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_employees_tenant", "employees", ["tenant_id"])
    op.create_index("ix_employees_published", "employees", ["tenant_id", "is_published"], postgresql_where="deleted_at IS NULL AND is_published = true")

    # Employee locales
    op.create_table(
        "employee_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("position", sa.String(255), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(70), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("meta_keywords", sa.String(255), nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("employee_id", "locale", name="uq_employee_locales"),
    )
    op.create_index("ix_employee_locales_slug", "employee_locales", ["locale", "slug"])

    # Employee practice areas (many-to-many)
    op.create_table(
        "employee_practice_areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("practice_area_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("practice_areas.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("employee_id", "practice_area_id", name="uq_employee_practice_areas"),
    )

    # Advantages
    op.create_table(
        "advantages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, default=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_advantages_tenant", "advantages", ["tenant_id"])
    op.create_index("ix_advantages_published", "advantages", ["tenant_id", "is_published"], postgresql_where="deleted_at IS NULL AND is_published = true")

    # Advantage locales
    op.create_table(
        "advantage_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("advantage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("advantages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("advantage_id", "locale", name="uq_advantage_locales"),
    )

    # Addresses
    op.create_table(
        "addresses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("address_type", sa.String(20), nullable=False, default="office"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("working_hours", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, default=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("address_type IN ('office', 'warehouse', 'showroom', 'other')", name="ck_addresses_type"),
    )
    op.create_index("ix_addresses_tenant", "addresses", ["tenant_id"])

    # Address locales
    op.create_table(
        "address_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("addresses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("street", sa.String(255), nullable=False),
        sa.Column("building", sa.String(50), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("address_id", "locale", name="uq_address_locales"),
    )

    # Contacts
    op.create_table(
        "contacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_type", sa.String(20), nullable=False),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, default=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("contact_type IN ('phone', 'email', 'whatsapp', 'telegram', 'viber', 'facebook', 'instagram', 'linkedin', 'youtube', 'other')", name="ck_contacts_type"),
    )
    op.create_index("ix_contacts_tenant", "contacts", ["tenant_id"])
    op.create_index("ix_contacts_type", "contacts", ["tenant_id", "contact_type"])


def downgrade() -> None:
    """Drop company tables."""
    op.drop_table("address_locales")
    op.drop_table("addresses")
    op.drop_table("contacts")
    op.drop_table("advantage_locales")
    op.drop_table("advantages")
    op.drop_table("employee_practice_areas")
    op.drop_table("employee_locales")
    op.drop_table("employees")
    op.drop_table("practice_area_locales")
    op.drop_table("practice_areas")
    op.drop_table("service_locales")
    op.drop_table("services")

