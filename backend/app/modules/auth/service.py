"""Authentication service - business logic for auth operations."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
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

    # ------------------------------------------------------------------
    # Smart login (optional tenant_id)
    # ------------------------------------------------------------------

    async def authenticate_smart(
        self,
        data: LoginRequest,
        tenant_id: UUID | None,
        ip_address: str | None = None,
    ) -> tuple[AdminUser, "TokenPair"] | dict:
        """Smart login that works with or without an explicit tenant_id.

        * ``tenant_id`` provided  -- delegates to :meth:`authenticate`.
        * ``tenant_id`` is None   -- looks up *all* active AdminUser
          records with the given email across tenants:
          - 0 matches  -> ``InvalidCredentialsError``
          - 1 match    -> auto-login (returns user + tokens)
          - 2+ matches -> returns a dict with ``status``,
            ``tenants`` list, and a short-lived ``selection_token``
        """
        if tenant_id is not None:
            return await self.authenticate(data, tenant_id, ip_address)

        from app.modules.tenants.models import Tenant, TenantDomain

        stmt = (
            select(AdminUser)
            .where(
                AdminUser.email == data.email,
                AdminUser.deleted_at.is_(None),
            )
            .options(
                selectinload(AdminUser.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission),
                selectinload(AdminUser.tenant),
            )
        )
        result = await self.db.execute(stmt)
        users = list(result.scalars().all())

        if not users:
            raise InvalidCredentialsError()

        # Verify password against the first user record (shared across tenants)
        if not verify_password(data.password, users[0].password_hash):
            raise InvalidCredentialsError()

        # Keep only users whose tenant is active and not deleted
        valid_users = [
            u for u in users
            if u.is_active
            and u.tenant is not None
            and u.tenant.is_active
            and u.tenant.deleted_at is None
        ]
        if not valid_users:
            raise InvalidCredentialsError("Account is disabled")

        # --- Single tenant: auto-login ---
        if len(valid_users) == 1:
            user = valid_users[0]
            user.last_login_at = datetime.now(UTC)
            user.last_login_ip = ip_address
            tokens = self._create_tokens(user)

            await self.audit.log(
                tenant_id=user.tenant_id,
                user_id=user.id,
                resource_type="auth",
                resource_id=user.id,
                action="login",
                ip_address=ip_address,
            )
            await self.db.commit()
            await self.db.refresh(user)
            return user, tokens

        # --- Multiple tenants: return selection payload ---
        tenants_info: list[dict] = []
        for u in valid_users:
            tenant = u.tenant
            domain_stmt = select(TenantDomain.domain).where(
                TenantDomain.tenant_id == tenant.id,
                TenantDomain.is_primary.is_(True),
            )
            domain_result = await self.db.execute(domain_stmt)
            admin_domain = domain_result.scalar_one_or_none()

            tenants_info.append({
                "tenant_id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "logo_url": tenant.logo_url,
                "primary_color": tenant.primary_color,
                "admin_domain": admin_domain,
                "role": u.role.name if u.role else None,
            })

        from app.core.security import create_selection_token

        selection_token = create_selection_token(
            email=data.email,
            tenant_ids=[str(u.tenant_id) for u in valid_users],
        )

        return {
            "status": "tenant_selection_required",
            "tenants": tenants_info,
            "selection_token": selection_token,
        }

    async def select_tenant(
        self,
        selection_token: str,
        tenant_id: UUID,
        ip_address: str | None = None,
    ) -> tuple[AdminUser, "TokenPair"]:
        """Finish a multi-tenant login after the user picks a tenant.

        Validates the short-lived ``selection_token`` issued by
        :meth:`authenticate_smart`, then returns a full token pair
        scoped to the chosen tenant.
        """
        from app.core.security import decode_selection_token

        payload = decode_selection_token(selection_token)
        email: str = payload["email"]
        allowed_ids: list[str] = payload.get("tenant_ids", [])

        if str(tenant_id) not in allowed_ids:
            raise InvalidCredentialsError("No access to this organization")

        await self._check_tenant_active(tenant_id)

        stmt = (
            select(AdminUser)
            .where(
                AdminUser.email == email,
                AdminUser.tenant_id == tenant_id,
                AdminUser.is_active.is_(True),
                AdminUser.deleted_at.is_(None),
            )
            .options(
                selectinload(AdminUser.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission),
            )
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise InvalidCredentialsError("No access to this organization")

        user.last_login_at = datetime.now(UTC)
        user.last_login_ip = ip_address
        tokens = self._create_tokens(user)

        await self.audit.log(
            tenant_id=tenant_id,
            user_id=user.id,
            resource_type="auth",
            resource_id=user.id,
            action="login",
            ip_address=ip_address,
            changes={"via": "select_tenant"},
        )
        await self.db.commit()
        await self.db.refresh(user)

        return user, tokens

    # ------------------------------------------------------------------
    # Multi-tenant: me/tenants & switch-tenant
    # ------------------------------------------------------------------

    async def get_user_tenants(
        self, current_user: "AdminUser", current_tenant_id: UUID
    ) -> dict:
        """Return all tenants the current user's *email* has access to.

        Looks up ``AdminUser`` rows across all tenants where ``email``
        matches, ``is_active=True`` and ``deleted_at IS NULL``.
        For each matching tenant also fetches primary admin domain from
        ``tenant_domains``.
        """
        from app.modules.tenants.models import Tenant, TenantDomain

        stmt = (
            select(AdminUser)
            .where(
                AdminUser.email == current_user.email,
                AdminUser.is_active.is_(True),
                AdminUser.deleted_at.is_(None),
            )
            .options(selectinload(AdminUser.tenant).selectinload(Tenant.settings))
        )
        result = await self.db.execute(stmt)
        user_rows = list(result.scalars().all())

        tenants_info = []
        for u in user_rows:
            tenant = u.tenant
            if tenant is None or tenant.deleted_at is not None or not tenant.is_active:
                continue

            # Primary domain lookup
            domain_stmt = select(TenantDomain.domain).where(
                TenantDomain.tenant_id == tenant.id,
                TenantDomain.is_primary.is_(True),
            )
            domain_result = await self.db.execute(domain_stmt)
            admin_domain = domain_result.scalar_one_or_none()

            tenants_info.append({
                "tenant_id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "logo_url": tenant.logo_url,
                "primary_color": tenant.primary_color,
                "admin_domain": admin_domain,
            })

        return {
            "current_tenant_id": str(current_tenant_id),
            "tenants": tenants_info,
        }

    async def switch_tenant(
        self,
        current_user: "AdminUser",
        target_tenant_id: UUID,
        ip_address: str | None = None,
        *,
        old_token_jti: str | None = None,
        old_token_expires_in: int = 0,
    ) -> TokenPair:
        """Switch the current user to a different tenant and issue new tokens.

        Validates that:
        1. The target tenant is active
        2. An AdminUser with the same email exists in the target tenant
        3. That AdminUser is active

        If ``old_token_jti`` is provided the previous access token is
        added to the Redis blacklist so it cannot be reused.

        Returns a fresh token pair scoped to the target tenant.
        """
        from app.modules.tenants.models import Tenant

        await self._check_tenant_active(target_tenant_id)

        stmt = (
            select(AdminUser)
            .where(
                AdminUser.email == current_user.email,
                AdminUser.tenant_id == target_tenant_id,
                AdminUser.is_active.is_(True),
                AdminUser.deleted_at.is_(None),
            )
            .options(
                selectinload(AdminUser.role)
                .selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
            )
        )
        result = await self.db.execute(stmt)
        target_user = result.scalar_one_or_none()

        if target_user is None:
            raise InvalidCredentialsError("No access to this organization")

        tokens = self._create_tokens(target_user)

        # Blacklist the old access token so it cannot be reused
        if old_token_jti:
            from app.core.redis import get_token_blacklist
            blacklist = get_token_blacklist()
            if blacklist:
                ttl = max(old_token_expires_in, 1)
                await blacklist.add(old_token_jti, ttl=ttl)

        await self.audit.log(
            tenant_id=target_tenant_id,
            user_id=target_user.id,
            resource_type="auth",
            resource_id=target_user.id,
            action="switch_tenant",
            ip_address=ip_address,
            changes={
                "from_tenant_id": str(current_user.tenant_id),
                "to_tenant_id": str(target_tenant_id),
            },
        )
        await self.db.commit()

        return tokens

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
            email_service = EmailService(db=self.db)
            await email_service.send_password_reset_email(
                to_email=user.email,
                first_name=user.first_name,
                reset_token=reset_token,
                tenant_id=tenant_id,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Failed to send password reset email to %s", email
            )

        return reset_token

    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset user password using a valid reset token.

        The new hash is also synced to every other ``AdminUser`` row
        with the same email so the user keeps a single password across
        all tenants.

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

        new_hash = hash_password(new_password)
        user.password_hash = new_hash
        user.force_password_change = False

        # Sync password to all other tenant records with the same email
        sync_stmt = (
            update(AdminUser)
            .where(
                AdminUser.email == user.email,
                AdminUser.id != user.id,
                AdminUser.deleted_at.is_(None),
            )
            .values(password_hash=new_hash)
        )
        await self.db.execute(sync_stmt)

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
        # Check email uniqueness in tenant (including soft-deleted to match DB constraint)
        existing = await self.db.execute(
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .where(AdminUser.email == data.email)
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
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            if "uq_admin_users_tenant_email" in str(exc):
                raise AlreadyExistsError("User", "email", data.email) from exc
            raise
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

                email_service = EmailService(db=self.db)
                await email_service.send_welcome_email(
                    to_email=data.email,
                    first_name=data.first_name,
                    tenant_name=tenant_name,
                    tenant_id=tenant_id,
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
        """Change user password. Clears force_password_change flag.

        The new hash is also synced to every other ``AdminUser`` row
        with the same email so the user keeps a single password across
        all tenants.
        """
        user = await self.get_by_id(user_id, tenant_id)

        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        new_hash = hash_password(data.new_password)
        user.password_hash = new_hash
        user.force_password_change = False
        await self.db.flush()

        # Sync password to all other tenant records with the same email
        sync_stmt = (
            update(AdminUser)
            .where(
                AdminUser.email == user.email,
                AdminUser.id != user.id,
                AdminUser.deleted_at.is_(None),
            )
            .values(password_hash=new_hash)
        )
        await self.db.execute(sync_stmt)

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

