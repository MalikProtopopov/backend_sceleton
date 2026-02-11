"""Authentication service - business logic for auth operations."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import (
    AlreadyExistsError,
    DuplicateRoleError,
    InvalidCredentialsError,
    InvalidTokenError,
    NotFoundError,
    RoleInUseError,
    SystemRoleModificationError,
    TenantInactiveError,
)
from app.core.security import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.base_service import update_many_to_many
from app.core.pagination import paginate_query
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
        self._audit: "AuditService | None" = None

    @property
    def audit(self) -> "AuditService":
        if self._audit is None:
            from app.core.audit import AuditService
            self._audit = AuditService(self.db)
        return self._audit

    async def _check_tenant_active(self, tenant_id: UUID) -> None:
        """Check if tenant is active. Raises TenantInactiveError if not."""
        from app.modules.tenants.models import Tenant

        stmt = select(Tenant.is_active).where(
            Tenant.id == tenant_id,
            Tenant.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        is_active = result.scalar_one_or_none()

        if is_active is None or not is_active:
            raise TenantInactiveError()

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
            TenantInactiveError: If tenant is suspended
        """
        # Check tenant is active before authenticating
        await self._check_tenant_active(tenant_id)

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
        user.last_login_at = datetime.now(UTC)
        user.last_login_ip = ip_address

        # Create tokens
        tokens = self._create_tokens(user)

        # Audit log
        await self.audit.log(
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
            TenantInactiveError: If tenant is suspended
        """
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Invalid token type")

        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

        # Check tenant is active before refreshing
        await self._check_tenant_active(tenant_id)

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

    # _log_action removed: use self.audit.log() from shared AuditService instead

    async def request_password_reset(self, email: str, tenant_id: UUID) -> str | None:
        """Generate a password reset token and send email.

        Returns the reset token if user found, None otherwise.
        Does NOT raise an error if user not found (security: prevent email enumeration).
        """
        from app.core.security import create_password_reset_token
        from app.modules.notifications.service import EmailService

        # Find user by email
        stmt = (
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.email == email)
            .where(AdminUser.deleted_at.is_(None))
            .where(AdminUser.is_active.is_(True))
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None  # Don't reveal that user doesn't exist

        # Generate reset token
        reset_token = create_password_reset_token(
            user_id=str(user.id),
            tenant_id=str(user.tenant_id),
            email=user.email,
        )

        # Send reset email
        try:
            email_service = EmailService()
            await email_service.send_password_reset_email(
                to_email=user.email,
                first_name=user.first_name,
                reset_token=reset_token,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to send password reset email to %s", email
            )

        return reset_token

    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset user password using a valid reset token.

        Args:
            token: Password reset JWT token
            new_password: New password to set

        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        from app.core.security import decode_password_reset_token

        payload = decode_password_reset_token(token)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tenant_id"])

        # Find user
        stmt = (
            select(AdminUser)
            .where(AdminUser.id == user_id)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise InvalidTokenError("User not found")

        # Update password
        user.password_hash = hash_password(new_password)
        user.force_password_change = False
        await self.db.commit()


class UserService(BaseService[AdminUser]):
    """Service for user management operations."""

    model = AdminUser

    def __init__(self, db: AsyncSession, actor_id: UUID | None = None) -> None:
        super().__init__(db)
        self._actor_id = actor_id
        self._audit: "AuditService | None" = None

    @property
    def audit(self) -> "AuditService":
        if self._audit is None:
            from app.core.audit import AuditService
            self._audit = AuditService(self.db)
        return self._audit

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(AdminUser.role)]

    async def get_by_id(self, user_id: UUID, tenant_id: UUID) -> AdminUser:
        """Get user by ID within tenant."""
        return await self._get_by_id(user_id, tenant_id)

    async def get_by_id_global(self, user_id: UUID) -> AdminUser:
        """Get user by ID without tenant restriction.

        Used by superuser / platform_owner when the user's tenant
        is unknown (e.g. navigating from the global user list).
        """
        stmt = (
            select(AdminUser)
            .where(AdminUser.id == user_id)
            .where(AdminUser.deleted_at.is_(None))
            .options(*self._get_default_options())
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("AdminUser", user_id)

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
        filters = []
        if is_active is not None:
            filters.append(AdminUser.is_active == is_active)

        base_query = self._build_base_query(tenant_id, filters=filters)

        # Add search filter separately (complex OR condition)
        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(
                (AdminUser.email.ilike(search_pattern)) |
                (AdminUser.full_name.ilike(search_pattern))
            )

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=self._get_default_options(),
            order_by=[AdminUser.created_at.desc()],
        )

    @transactional
    async def create(self, tenant_id: UUID, data: UserCreate) -> AdminUser:
        """Create a new user.
        
        Sets force_password_change=True for new users.
        Sends welcome email when send_credentials=True.
        """
        # Check email uniqueness in tenant
        existing = await self.db.execute(
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.email == data.email)
            .where(AdminUser.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsError("User", "email", data.email)

        # Create user with force_password_change=True
        user = AdminUser(
            tenant_id=tenant_id,
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            role_id=data.role_id,
            is_active=data.is_active,
            force_password_change=True,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(user, ["role"])

        # Audit log: user created
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id,
            resource_type="user",
            resource_id=user.id,
            action="create",
            changes={"email": user.email, "first_name": user.first_name, "last_name": user.last_name},
        )

        # Send welcome email if requested
        if data.send_credentials:
            try:
                from app.modules.notifications.service import EmailService
                from app.modules.tenants.models import Tenant

                # Get tenant name for the email
                tenant_stmt = select(Tenant.name).where(Tenant.id == tenant_id)
                tenant_result = await self.db.execute(tenant_stmt)
                tenant_name = tenant_result.scalar_one_or_none() or "Platform"

                email_service = EmailService()
                await email_service.send_welcome_email(
                    to_email=data.email,
                    first_name=data.first_name,
                    tenant_name=tenant_name,
                )
            except Exception:
                # Don't fail user creation if email sending fails
                import logging
                logging.getLogger(__name__).warning(
                    "Failed to send welcome email to %s", data.email
                )

        return user

    @transactional
    async def update(
        self, user_id: UUID, tenant_id: UUID, data: UserUpdate
    ) -> AdminUser:
        """Update user with optimistic locking."""
        user = await self.get_by_id(user_id, tenant_id)
        user.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        # Track changes for audit log
        changes: dict = {}
        for field, value in update_data.items():
            old_value = getattr(user, field, None)
            if old_value != value:
                changes[field] = {"old": str(old_value) if old_value is not None else None, "new": str(value)}
            setattr(user, field, value)

        await self.db.flush()

        # Audit log: user updated
        if changes:
            await self.audit.log(
                tenant_id=tenant_id,
                user_id=self._actor_id,
                resource_type="user",
                resource_id=user_id,
                action="update",
                changes=changes,
            )

        await self.db.refresh(user)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(user, ["role"])

        return user

    @transactional
    async def change_password(
        self, user_id: UUID, tenant_id: UUID, data: PasswordChange
    ) -> None:
        """Change user password. Clears force_password_change flag."""
        user = await self.get_by_id(user_id, tenant_id)

        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        user.password_hash = hash_password(data.new_password)
        user.force_password_change = False
        await self.db.flush()

        # Audit log: password changed
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id or user_id,
            resource_type="user",
            resource_id=user_id,
            action="update",
            changes={"password": {"old": "***", "new": "***"}, "force_password_change": {"old": "True", "new": "False"}},
        )

    @transactional
    async def soft_delete(self, user_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a user."""
        await self._soft_delete(user_id, tenant_id)

        # Audit log: user deleted
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id,
            resource_type="user",
            resource_id=user_id,
            action="delete",
        )


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

