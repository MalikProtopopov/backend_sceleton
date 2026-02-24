"""Auth module - role service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import update_many_to_many
from app.core.database import transactional
from app.core.exceptions import (
    DuplicateRoleError,
    NotFoundError,
    RoleInUseError,
    SystemRoleModificationError,
)
from app.modules.auth.models import AdminUser, Permission, Role, RolePermission


class RoleService:
    """Service for role management operations."""

    def __init__(self, db: AsyncSession, actor_id: UUID | None = None) -> None:
        self.db = db
        self._actor_id = actor_id
        self._audit: "AuditService | None" = None

    @property
    def audit(self) -> "AuditService":
        if self._audit is None:
            from app.core.audit import AuditService
            self._audit = AuditService(self.db)
        return self._audit

    async def get_by_id(self, role_id: UUID, tenant_id: UUID) -> Role:
        """Get role by ID within tenant."""
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .where(Role.tenant_id == tenant_id)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
        )
        result = await self.db.execute(stmt)
        role = result.scalar_one_or_none()

        if not role:
            raise NotFoundError("Role", role_id)

        return role

    async def list_roles(self, tenant_id: UUID) -> list[Role]:
        """List all roles in tenant."""
        stmt = (
            select(Role)
            .where(Role.tenant_id == tenant_id)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .order_by(Role.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_permissions(self) -> list[Permission]:
        """List all available permissions."""
        stmt = select(Permission).order_by(Permission.resource, Permission.action)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def create_role(
        self,
        tenant_id: UUID,
        name: str,
        description: str | None,
        permission_ids: list[UUID],
    ) -> Role:
        """Create a new role."""
        # Check if role with same name exists
        existing = await self.db.execute(
            select(Role)
            .where(Role.tenant_id == tenant_id)
            .where(Role.name == name)
        )
        if existing.scalar_one_or_none():
            raise DuplicateRoleError(name)

        role = Role(
            tenant_id=tenant_id,
            name=name,
            description=description,
            is_system=False,
        )
        self.db.add(role)
        await self.db.flush()

        # Add permissions
        for perm_id in permission_ids:
            rp = RolePermission(role_id=role.id, permission_id=perm_id)
            self.db.add(rp)

        await self.db.flush()

        # Audit log: role created
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id,
            resource_type="role",
            resource_id=role.id,
            action="create",
            changes={"name": name, "description": description},
        )

        await self.db.refresh(role)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(role, ["role_permissions"])
        return role

    @transactional
    async def update_role(
        self,
        role_id: UUID,
        tenant_id: UUID,
        name: str | None,
        description: str | None,
        permission_ids: list[UUID] | None,
    ) -> Role:
        """Update a role."""
        role = await self.get_by_id(role_id, tenant_id)

        if role.is_system:
            raise SystemRoleModificationError("modify")

        if name is not None:
            # Check for duplicate name
            existing = await self.db.execute(
                select(Role)
                .where(Role.tenant_id == tenant_id)
                .where(Role.name == name)
                .where(Role.id != role_id)
            )
            if existing.scalar_one_or_none():
                raise DuplicateRoleError(name)
            role.name = name

        if description is not None:
            role.description = description

        # Update permissions if provided
        if permission_ids is not None:
            await update_many_to_many(
                self.db,
                role,
                "role_permissions",
                permission_ids,
                RolePermission,
                "role_id",
                "permission_id",
            )

        await self.db.flush()

        # Audit log: role updated
        changes: dict = {}
        if name is not None:
            changes["name"] = name
        if description is not None:
            changes["description"] = description
        if permission_ids is not None:
            changes["permissions_updated"] = True
        if changes:
            await self.audit.log(
                tenant_id=tenant_id,
                user_id=self._actor_id,
                resource_type="role",
                resource_id=role_id,
                action="update",
                changes=changes,
            )

        await self.db.refresh(role)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(role, ["role_permissions"])
        return role

    @transactional
    async def delete_role(self, role_id: UUID, tenant_id: UUID) -> None:
        """Delete a role."""
        role = await self.get_by_id(role_id, tenant_id)

        if role.is_system:
            raise SystemRoleModificationError("delete")

        # Check if role is in use
        users_with_role = await self.db.execute(
            select(func.count())
            .select_from(AdminUser)
            .where(AdminUser.role_id == role_id)
            .where(AdminUser.deleted_at.is_(None))
        )
        if users_with_role.scalar() or 0 > 0:
            raise RoleInUseError(role.name)

        # Audit log: role deleted
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id,
            resource_type="role",
            resource_id=role_id,
            action="delete",
            changes={"name": role.name},
        )

        await self.db.delete(role)
        await self.db.flush()
