"""Auth module - authentication service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.database import transactional
from app.core.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    TenantInactiveError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import AdminUser, Role, RolePermission
from app.modules.auth.schemas import LoginRequest, TokenPair


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

    @transactional
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

        await self.db.flush()
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

    @transactional
    async def authenticate_smart(
        self,
        data: LoginRequest,
        tenant_id: UUID | None,
        ip_address: str | None = None,
        request_origin: str | None = None,
    ) -> tuple[AdminUser, "TokenPair"] | dict:
        """Smart login that works with or without an explicit tenant_id.

        * ``tenant_id`` provided **and user exists in that tenant**
          -- delegates to :meth:`authenticate`.
        * Otherwise -- looks up *all* active AdminUser records with the
          given email across tenants:
          - 0 matches  -> ``InvalidCredentialsError``
          - 1 match    -> auto-login (returns user + tokens)
          - 2+ matches -> returns a dict with ``status``,
            ``tenants`` list, and a short-lived ``selection_token``

        This ensures that a user logging in from any admin domain
        (even one mapped to a different tenant) can still authenticate.
        """
        if tenant_id is not None:
            exists_stmt = select(AdminUser.id).where(
                AdminUser.tenant_id == tenant_id,
                AdminUser.email == data.email,
                AdminUser.deleted_at.is_(None),
            )
            exists_result = await self.db.execute(exists_stmt)
            if exists_result.scalar_one_or_none() is not None:
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

        # --- Single tenant: auto-login or redirect ---
        if len(valid_users) == 1:
            user = valid_users[0]

            # Cross-tenant guard: user found in a different tenant than
            # the one resolved from the admin domain.
            is_cross_tenant = (
                tenant_id is not None and user.tenant_id != tenant_id
            )
            if is_cross_tenant:
                is_privileged = user.is_superuser or (
                    user.role and user.role.name == "platform_owner"
                )
                if not is_privileged:
                    tenant = user.tenant
                    domain_stmt = select(TenantDomain.domain).where(
                        TenantDomain.tenant_id == tenant.id,
                        TenantDomain.is_primary.is_(True),
                    )
                    domain_result = await self.db.execute(domain_stmt)
                    admin_domain = domain_result.scalar_one_or_none()

                    # If the request already comes from the user's own tenant
                    # domain (custom domain like admin.yastvo.com), skip the
                    # redirect and log in directly against the correct tenant.
                    origin_host = None
                    if request_origin:
                        from urllib.parse import urlparse
                        origin_host = urlparse(request_origin).hostname

                    if admin_domain and origin_host and origin_host == admin_domain:
                        return await self.authenticate(
                            data, user.tenant_id, ip_address
                        )

                    return {
                        "status": "tenant_redirect_required",
                        "tenant": {
                            "tenant_id": str(tenant.id),
                            "name": tenant.name,
                            "slug": tenant.slug,
                            "logo_url": tenant.logo_url,
                            "primary_color": tenant.primary_color,
                            "admin_domain": admin_domain,
                            "role": user.role.name if user.role else None,
                        },
                    }

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
            await self.db.flush()
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

    @transactional
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
        await self.db.flush()
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

    @transactional
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
        await self.db.flush()

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

    @transactional
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

        await self.db.flush()

    @transactional
    async def log_logout(self, tenant_id: UUID, user_id: UUID) -> None:
        """Record an audit log entry for logout."""
        await self.audit.log(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type="auth",
            resource_id=user_id,
            action="logout",
        )
