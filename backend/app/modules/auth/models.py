"""Authentication and authorization database models."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)

if TYPE_CHECKING:
    from app.modules.tenants.models import Tenant


class Role(Base, UUIDMixin, TimestampMixin):
    """User roles for RBAC.

    Default roles:
    - admin: Full access to all features
    - content_manager: Manage articles, FAQ, services (no SEO, no settings)
    - marketer: Manage cases, reviews, SEO, view leads
    """

    __tablename__ = "roles"

    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Role name (e.g., 'admin', 'content_manager', 'marketer')
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Human-readable description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Is this a system role (cannot be deleted)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    users: Mapped[list["AdminUser"]] = relationship(
        "AdminUser",
        back_populates="role",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),
        Index("ix_roles_tenant", "tenant_id"),
        CheckConstraint("char_length(name) >= 2", name="ck_roles_name_min_length"),
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class Permission(Base, UUIDMixin, TimestampMixin):
    """Available permissions in the system.

    Permissions follow pattern: resource:action
    Examples: articles:create, articles:read, articles:update, articles:delete
    """

    __tablename__ = "permissions"

    # Permission code (e.g., 'articles:create')
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Human-readable name
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resource this permission belongs to (e.g., 'articles')
    resource: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Action (e.g., 'create', 'read', 'update', 'delete')
    action: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        Index("ix_permissions_resource_action", "resource", "action"),
        CheckConstraint(
            "code ~ '^[a-z_]+:[a-z_]+$'",
            name="ck_permissions_code_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class RolePermission(Base, UUIDMixin):
    """Many-to-many relationship between roles and permissions."""

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship("Permission", lazy="joined")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions"),
        Index("ix_role_permissions_role", "role_id"),
        Index("ix_role_permissions_permission", "permission_id"),
    )


class AdminUser(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin):
    """Admin users for the CMS."""

    __tablename__ = "admin_users"

    # Tenant - explicit ForeignKey for relationship support
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Authentication
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Profile
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Last activity
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Role
    role_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    role: Mapped["Role | None"] = relationship("Role", back_populates="users")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_admin_users_tenant_email"),
        Index("ix_admin_users_email", "email"),
        Index(
            "ix_admin_users_active",
            "tenant_id",
            "is_active",
            postgresql_where="deleted_at IS NULL AND is_active = true",
        ),
        CheckConstraint("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'", 
                       name="ck_admin_users_email_format"),
    )

    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<AdminUser {self.email}>"


class AuditLog(Base, UUIDMixin):
    """Audit log for tracking all changes.

    Records who did what, when, and what changed.
    Note: Audit logs are immutable, so no updated_at field.
    """

    __tablename__ = "audit_logs"

    # Tenant - explicit ForeignKey for relationship support
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Who performed the action
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    user: Mapped["AdminUser | None"] = relationship("AdminUser", lazy="selectin")

    # What was affected
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)

    # What action was performed
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create, update, delete

    # What changed (before/after for updates)
    changes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Timestamp (only created_at since logs are immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_logs_tenant_resource", "tenant_id", "resource_type", "resource_id"),
        Index("ix_audit_logs_user", "user_id"),
        Index("ix_audit_logs_created", "tenant_id", "created_at"),
        CheckConstraint(
            "action IN ('create', 'update', 'delete', 'login', 'logout')",
            name="ck_audit_logs_action",
        ),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.resource_type}/{self.resource_id}>"


# Default permissions for the system
DEFAULT_PERMISSIONS = [
    # Articles
    ("articles:create", "Create Articles", "articles", "create"),
    ("articles:read", "Read Articles", "articles", "read"),
    ("articles:update", "Update Articles", "articles", "update"),
    ("articles:delete", "Delete Articles", "articles", "delete"),
    ("articles:publish", "Publish Articles", "articles", "publish"),
    # Services
    ("services:create", "Create Services", "services", "create"),
    ("services:read", "Read Services", "services", "read"),
    ("services:update", "Update Services", "services", "update"),
    ("services:delete", "Delete Services", "services", "delete"),
    # Employees
    ("employees:create", "Create Employees", "employees", "create"),
    ("employees:read", "Read Employees", "employees", "read"),
    ("employees:update", "Update Employees", "employees", "update"),
    ("employees:delete", "Delete Employees", "employees", "delete"),
    # Cases
    ("cases:create", "Create Cases", "cases", "create"),
    ("cases:read", "Read Cases", "cases", "read"),
    ("cases:update", "Update Cases", "cases", "update"),
    ("cases:delete", "Delete Cases", "cases", "delete"),
    # Reviews
    ("reviews:create", "Create Reviews", "reviews", "create"),
    ("reviews:read", "Read Reviews", "reviews", "read"),
    ("reviews:update", "Update Reviews", "reviews", "update"),
    ("reviews:delete", "Delete Reviews", "reviews", "delete"),
    # FAQ
    ("faq:create", "Create FAQ", "faq", "create"),
    ("faq:read", "Read FAQ", "faq", "read"),
    ("faq:update", "Update FAQ", "faq", "update"),
    ("faq:delete", "Delete FAQ", "faq", "delete"),
    # Inquiries
    ("inquiries:read", "Read Inquiries", "inquiries", "read"),
    ("inquiries:update", "Update Inquiries", "inquiries", "update"),
    ("inquiries:delete", "Delete Inquiries", "inquiries", "delete"),
    # SEO
    ("seo:read", "Read SEO Settings", "seo", "read"),
    ("seo:update", "Update SEO Settings", "seo", "update"),
    # Settings
    ("settings:read", "Read Settings", "settings", "read"),
    ("settings:update", "Update Settings", "settings", "update"),
    # Users
    ("users:create", "Create Users", "users", "create"),
    ("users:read", "Read Users", "users", "read"),
    ("users:update", "Update Users", "users", "update"),
    ("users:delete", "Delete Users", "users", "delete"),
    # Platform (PLATFORM_OWNER only)
    ("platform:read", "Read Platform Settings", "platform", "read"),
    ("platform:update", "Update Platform Settings", "platform", "update"),
    # Features (module management)
    ("features:read", "Read Feature Flags", "features", "read"),
    ("features:update", "Update Feature Flags", "features", "update"),
    # Audit
    ("audit:read", "Read Audit Logs", "audit", "read"),
]

# Default role configurations
DEFAULT_ROLES = {
    "platform_owner": {
        "description": "Platform administrator - manages modules, settings, and has full access",
        "permissions": ["*"],  # All permissions including platform and features
    },
    "site_owner": {
        "description": "Site administrator - manages content and users",
        "permissions": [
            "articles:*",
            "services:*",
            "employees:*",
            "cases:*",
            "reviews:*",
            "faq:*",
            "inquiries:*",
            "seo:*",
            "settings:*",
            "users:*",
            "audit:read",
        ],
    },
    "content_manager": {
        "description": "Manage articles, FAQ, services",
        "permissions": [
            "articles:*",
            "services:read",
            "services:update",
            "employees:read",
            "faq:*",
        ],
    },
    "marketer": {
        "description": "Manage cases, reviews, SEO, view leads",
        "permissions": [
            "cases:*",
            "reviews:*",
            "seo:*",
            "inquiries:read",
        ],
    },
    "editor": {
        "description": "Create and edit content drafts",
        "permissions": [
            "articles:create",
            "articles:read",
            "articles:update",
            "faq:create",
            "faq:read",
            "faq:update",
        ],
    },
}

