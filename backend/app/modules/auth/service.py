"""Authentication service - business logic for auth operations."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.database import transactional
from app.core.exceptions import (
    AlreadyExistsError,
    DuplicateRoleError,
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
    RoleInUseError,
    SystemRoleModificationError,
)
from app.core.security import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import AdminUser, AuditLog, Permission, Role, RolePermission
from app.modules.auth.schemas import (
    LoginRequest,
    PasswordChange,
    TokenPair,
    UserCreate,
    UserUpdate,
)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def authenticate(
        self,
        data: LoginRequest,
        tenant_id: UUID,
        ip_address: str | None = None,
    ) -> tuple[AdminUser, TokenPair]:
        """Authenticate user and return tokens.

        Args:
            data: Login credentials
            tenant_id: Tenant to authenticate against
            ip_address: Client IP for audit logging

        Returns:
            Tuple of (user, tokens)

        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        # Find user by email in tenant
        stmt = (
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.email == data.email)
            .where(AdminUser.deleted_at.is_(None))
            .options(
                selectinload(AdminUser.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError("Account is disabled")

        # Update last login
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address

        # Create tokens
        tokens = self._create_tokens(user)

        # Audit log
        await self._log_action(
            tenant_id=tenant_id,
            user_id=user.id,
            resource_type="auth",
            resource_id=user.id,
            action="login",
            ip_address=ip_address,
        )

        await self.db.commit()
        
        # Refresh user to get updated_at from database (updated by onupdate trigger)
        await self.db.refresh(user)

        return user, tokens

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token pair

        Raises:
            InvalidTokenError: If refresh token is invalid
        """
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid token type")

        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

        # Get user
        stmt = (
            select(AdminUser)
            .where(AdminUser.id == user_id)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.deleted_at.is_(None))
            .where(AdminUser.is_active.is_(True))
            .options(
                selectinload(AdminUser.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise InvalidTokenError("User not found")

        return self._create_tokens(user)

    def _create_tokens(self, user: AdminUser) -> TokenPair:
        """Create access and refresh tokens for user."""
        # Build token payload
        token_data = {
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "email": user.email,
            "is_superuser": user.is_superuser,
        }

        # Add role and permissions
        if user.role:
            token_data["role"] = user.role.name
            token_data["permissions"] = [
                rp.permission.code for rp in user.role.role_permissions
            ]

        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    async def _log_action(
        self,
        tenant_id: UUID,
        user_id: UUID | None,
        resource_type: str,
        resource_id: UUID,
        action: str,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Create audit log entry."""
        log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)


class UserService:
    """Service for user management operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: UUID, tenant_id: UUID) -> AdminUser:
        """Get user by ID within tenant."""
        stmt = (
            select(AdminUser)
            .where(AdminUser.id == user_id)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.deleted_at.is_(None))
            .options(selectinload(AdminUser.role))
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User", user_id)

        return user

    async def list_users(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[AdminUser], int]:
        """List users in tenant with pagination."""
        base_query = (
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.deleted_at.is_(None))
        )

        if is_active is not None:
            base_query = base_query.where(AdminUser.is_active == is_active)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(
                (AdminUser.email.ilike(search_pattern)) |
                (AdminUser.full_name.ilike(search_pattern))
            )

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get paginated results
        stmt = (
            base_query.options(selectinload(AdminUser.role))
            .order_by(AdminUser.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        return users, total

    @transactional
    async def create(self, tenant_id: UUID, data: UserCreate) -> AdminUser:
        """Create a new user."""
        # Check email uniqueness in tenant
        existing = await self.db.execute(
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.email == data.email)
            .where(AdminUser.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsError("User", "email", data.email)

        # Create user
        user = AdminUser(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role_id=data.role_id,
            is_active=data.is_active,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(user, ["role"])

        return user

    @transactional
    async def update(
        self, user_id: UUID, tenant_id: UUID, data: UserUpdate
    ) -> AdminUser:
        """Update user with optimistic locking."""
        user = await self.get_by_id(user_id, tenant_id)
        user.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(user, field, value)

        await self.db.flush()
        await self.db.refresh(user)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(user, ["role"])

        return user

    @transactional
    async def change_password(
        self, user_id: UUID, tenant_id: UUID, data: PasswordChange
    ) -> None:
        """Change user password."""
        user = await self.get_by_id(user_id, tenant_id)

        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        user.password_hash = hash_password(data.new_password)
        await self.db.flush()

    @transactional
    async def soft_delete(self, user_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a user."""
        user = await self.get_by_id(user_id, tenant_id)
        user.soft_delete()
        await self.db.flush()


class RoleService:
    """Service for role management operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
            # Remove existing
            for rp in role.role_permissions:
                await self.db.delete(rp)

            # Add new
            for perm_id in permission_ids:
                rp = RolePermission(role_id=role.id, permission_id=perm_id)
                self.db.add(rp)

        await self.db.flush()
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

        await self.db.delete(role)
        await self.db.flush()

