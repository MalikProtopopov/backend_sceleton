"""Security utilities - JWT, password hashing, RBAC."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import bcrypt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import (
    AuthenticationError,
    FeatureDisabledError,
    InsufficientRoleError,
    InvalidTokenError,
    PermissionDeniedError,
    TenantInactiveError,
    TokenExpiredError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


# ============================================================================
# Password Utilities
# ============================================================================


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Bcrypt has a 72 byte limit, so we truncate if necessary.
    """
    # Bcrypt has a 72 byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Bcrypt has a 72 byte limit, so we truncate if necessary.
    """
    try:
        # Bcrypt has a 72 byte limit, truncate if necessary
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


# ============================================================================
# JWT Utilities
# ============================================================================


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with unique jti for blacklist support."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
        "jti": str(uuid4()),  # Unique token ID for blacklist
    })

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT refresh token with unique jti for blacklist support."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
        "jti": str(uuid4()),  # Unique token ID for blacklist
    })

    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except JWTError:
        raise InvalidTokenError()


def create_password_reset_token(user_id: str, tenant_id: str, email: str) -> str:
    """Create a short-lived JWT token for password reset (1 hour)."""
    data = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "type": "password_reset",
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    return jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_password_reset_token(token: str) -> dict[str, Any]:
    """Decode and validate a password reset token."""
    payload = decode_token(token)
    if payload.get("type") != "password_reset":
        raise InvalidTokenError("Invalid token type")
    return payload


def create_selection_token(email: str, tenant_ids: list[str]) -> str:
    """Create a short-lived JWT (15 min) for the tenant-selection step.

    Issued when a user with access to multiple tenants logs in
    without specifying ``X-Tenant-ID``.  The token carries the
    pre-verified email and the list of allowed tenant IDs so
    ``POST /auth/select-tenant`` can finish login without asking
    for the password again.
    """
    data = {
        "email": email,
        "tenant_ids": tenant_ids,
        "type": "tenant_selection",
        "exp": datetime.now(UTC) + timedelta(minutes=15),
        "iat": datetime.now(UTC),
        "jti": str(uuid4()),
    }
    return jwt.encode(data, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_selection_token(token: str) -> dict[str, Any]:
    """Decode and validate a tenant-selection token."""
    payload = decode_token(token)
    if payload.get("type") != "tenant_selection":
        raise InvalidTokenError("Invalid token type")
    return payload


# ============================================================================
# Token Payload Schemas
# ============================================================================


class TokenPayload:
    """Parsed JWT token payload."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.user_id: UUID = UUID(payload["sub"])
        self.tenant_id: UUID = UUID(payload["tenant_id"])
        self.email: str = payload["email"]
        self.role: str | None = payload.get("role")
        self.permissions: list[str] = payload.get("permissions", [])
        self.is_superuser: bool = payload.get("is_superuser", False)
        self.token_type: str = payload.get("type", "access")
        self.exp: datetime = datetime.fromtimestamp(payload["exp"], tz=UTC)
        self.jti: str | None = payload.get("jti")  # Token ID for blacklist
    
    @property
    def expires_in_seconds(self) -> int:
        """Get remaining TTL in seconds."""
        remaining = self.exp - datetime.now(UTC)
        return max(0, int(remaining.total_seconds()))


# ============================================================================
# FastAPI Dependencies
# ============================================================================


async def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TokenPayload:
    """Dependency to get current token payload.

    Raises AuthenticationError if no token or invalid token.
    Checks token blacklist for revoked tokens.
    """
    if credentials is None:
        raise AuthenticationError("Authorization header required")

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise InvalidTokenError("Invalid token type")
    
    # Check if token is blacklisted (revoked on logout)
    jti = payload.get("jti")
    if jti:
        from app.core.redis import get_token_blacklist
        blacklist = await get_token_blacklist()
        if blacklist and await blacklist.is_blacklisted(jti):
            logger.warning("blacklisted_token_used", jti=jti[:8])
            raise InvalidTokenError("Token has been revoked")

    return TokenPayload(payload)


async def _check_tenant_active(tenant_id: UUID, db: AsyncSession) -> None:
    """Check if tenant is active using Redis cache with DB fallback.
    
    Raises TenantInactiveError if tenant is suspended.
    Uses Redis cache (30s TTL) to avoid DB hit on every request.
    """
    from app.core.redis import get_tenant_status_cache
    from app.modules.tenants.models import Tenant

    tenant_id_str = str(tenant_id)
    
    # Try Redis cache first
    cache = await get_tenant_status_cache()
    if cache:
        cached_status = await cache.is_tenant_active(tenant_id_str)
        if cached_status is not None:
            if not cached_status:
                raise TenantInactiveError()
            return
    
    # Cache miss -- query DB
    stmt = select(Tenant.is_active).where(
        Tenant.id == tenant_id,
        Tenant.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    is_active = result.scalar_one_or_none()
    
    # Cache the result
    if cache and is_active is not None:
        await cache.set_status(tenant_id_str, is_active)
    
    if is_active is None or not is_active:
        raise TenantInactiveError()


async def get_current_user(
    token: TokenPayload = Depends(get_current_token),
    db: AsyncSession = Depends(get_db),
) -> "AdminUser":  # type: ignore
    """Dependency to get current authenticated user.

    Loads user from database and validates they're active.
    Also checks that tenant is active (with superuser bypass).
    """
    from app.modules.auth.models import AdminUser

    stmt = (
        select(AdminUser)
        .where(AdminUser.id == token.user_id)
        .where(AdminUser.deleted_at.is_(None))
        .where(AdminUser.is_active.is_(True))
        .options(selectinload(AdminUser.role))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found or inactive")

    # Check tenant is active (superusers and platform_owners bypass)
    is_platform_privileged = user.is_superuser or (
        user.role and user.role.name == "platform_owner"
    )
    if not is_platform_privileged:
        await _check_tenant_active(token.tenant_id, db)

    return user


async def get_current_active_user(
    user: "AdminUser" = Depends(get_current_user),  # type: ignore
) -> "AdminUser":  # type: ignore
    """Dependency to ensure user is active."""
    if not user.is_active:
        raise AuthenticationError("User account is disabled")
    return user


def get_current_tenant_id(
    token: TokenPayload = Depends(get_current_token),
) -> UUID:
    """Dependency to get current tenant ID from token."""
    return token.tenant_id


# ============================================================================
# Permission Checker Dependencies
# ============================================================================


class PermissionChecker:
    """Dependency class for checking user permissions.

    Usage:
        @router.post("/articles")
        async def create_article(
            user: AdminUser = Depends(PermissionChecker("articles:create")),
        ):
            ...
    """

    def __init__(self, required_permission: str) -> None:
        self.required_permission = required_permission

    async def __call__(
        self,
        user: "AdminUser" = Depends(get_current_active_user),  # type: ignore
    ) -> "AdminUser":  # type: ignore
        """Check if user has required permission."""
        # Superusers have all permissions
        if user.is_superuser:
            return user

        # Get user permissions from role
        if user.role:
            user_permissions = [rp.permission.code for rp in user.role.role_permissions]

            # Check for wildcard permission (e.g., 'articles:*')
            resource = self.required_permission.split(":")[0]
            wildcard = f"{resource}:*"

            if (
                self.required_permission in user_permissions
                or wildcard in user_permissions
                or "*" in user_permissions
            ):
                return user

        raise PermissionDeniedError(
            required_permission=self.required_permission,
        )


class RoleChecker:
    """Dependency class for checking user role.

    Usage:
        @router.delete("/tenants/{id}")
        async def delete_tenant(
            user: AdminUser = Depends(RoleChecker("admin")),
        ):
            ...
    """

    def __init__(self, required_role: str) -> None:
        self.required_role = required_role

    async def __call__(
        self,
        user: "AdminUser" = Depends(get_current_active_user),  # type: ignore
    ) -> "AdminUser":  # type: ignore
        """Check if user has required role."""
        # Superusers bypass role checks
        if user.is_superuser:
            return user

        if user.role and user.role.name == self.required_role:
            return user

        raise InsufficientRoleError(required_role=self.required_role)


class PlatformOwnerChecker:
    """Dependency class for checking platform owner access.

    Platform owners have full access to platform-level features like
    feature flags, tenant settings, and system configuration.

    Usage:
        @router.patch("/feature-flags/{name}")
        async def toggle_feature(
            user: AdminUser = Depends(require_platform_owner),
        ):
            ...
    """

    async def __call__(
        self,
        user: "AdminUser" = Depends(get_current_active_user),  # type: ignore
    ) -> "AdminUser":  # type: ignore
        """Check if user is platform owner or superuser."""
        # Superusers always have platform owner access
        if user.is_superuser:
            return user

        # Check for platform_owner role
        if user.role and user.role.name == "platform_owner":
            return user

        raise PermissionDeniedError(
            required_permission="platform:*",
        )


# Convenience instance for dependency injection
require_platform_owner = PlatformOwnerChecker()


class FeatureChecker:
    """Dependency class for checking feature flags.

    Usage:
        @router.get("/cases")
        async def list_cases(
            _: None = Depends(FeatureChecker("cases_module")),
        ):
            ...
    """

    def __init__(self, feature_name: str) -> None:
        self.feature_name = feature_name

    async def __call__(
        self,
        tenant_id: UUID = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        """Check if feature is enabled for tenant."""
        from app.modules.tenants.service import FeatureFlagService

        service = FeatureFlagService(db)
        if not await service.is_enabled(tenant_id, self.feature_name):
            raise FeatureDisabledError(self.feature_name)


# Convenience type alias - uses TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.auth.models import AdminUser as AdminUserType
    CurrentUser = AdminUserType
else:
    CurrentUser = "AdminUser"  # type: ignore

