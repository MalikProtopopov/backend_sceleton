"""API routes for authentication."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, get_optional_tenant_from_header, get_tenant_from_header
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.image_upload import image_upload_service
from app.core.logging import get_logger
from app.core.redis import get_token_blacklist
from app.core.security import (
    PermissionChecker,
    TokenPayload,
    get_current_active_user,
    get_current_tenant_id,
    get_current_token,
)

logger = get_logger(__name__)
from app.modules.auth.models import AdminUser
from app.modules.auth.schemas import (
    EnabledFeaturesResponse,
    FeatureCatalogItem,
    FeatureCatalogResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MyTenantsResponse,
    PasswordChange,
    PermissionListResponse,
    PermissionResponse,
    ResetPasswordRequest,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
    SelectTenantRequest,
    SwitchTenantRequest,
    TenantAccessInfo,
    TenantOption,
    TenantRedirectRequired,
    TenantSelectionRequired,
    TokenPair,
    TokenRefresh,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.modules.tenants.service import FeatureFlagService
from app.modules.auth.service import AuthService, RoleService, UserService

router = APIRouter()


# ============================================================================
# Authentication Routes
# ============================================================================


@router.post(
    "/login",
    response_model=None,
    summary="Login",
    description=(
        "Authenticate user and receive JWT tokens. "
        "X-Tenant-ID header is optional: when omitted the backend "
        "auto-detects the tenant (or returns a tenant-selection "
        "response if the user belongs to multiple organisations)."
    ),
    responses={
        200: {
            "description": "Login success, tenant selection, or tenant redirect",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Single tenant (or X-Tenant-ID provided)",
                            "value": {
                                "status": "success",
                                "tokens": {
                                    "access_token": "eyJ...",
                                    "refresh_token": "eyJ...",
                                    "token_type": "bearer",
                                    "expires_in": 1800,
                                },
                                "user": {"id": "...", "email": "user@example.com"},
                            },
                        },
                        "selection": {
                            "summary": "Multiple tenants available",
                            "value": {
                                "status": "tenant_selection_required",
                                "tenants": [
                                    {
                                        "tenant_id": "...",
                                        "name": "Company 1",
                                        "slug": "company1",
                                        "role": "site_owner",
                                    }
                                ],
                                "selection_token": "eyJ...",
                            },
                        },
                        "redirect": {
                            "summary": "User belongs to a different organization",
                            "value": {
                                "status": "tenant_redirect_required",
                                "tenant": {
                                    "tenant_id": "...",
                                    "name": "Other Org",
                                    "slug": "other-org",
                                    "admin_domain": "admin.other-org.com",
                                    "role": "editor",
                                },
                                "message": "Your account belongs to a different organization",
                            },
                        },
                    }
                }
            },
        }
    },
)
async def login(
    data: LoginRequest,
    request: Request,
    tenant_id: UUID | None = Depends(get_optional_tenant_from_header),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse | TenantSelectionRequired | TenantRedirectRequired:
    """Authenticate user and return tokens.

    Rate limited to 10 attempts per minute per IP address.
    """
    ip_address = request.client.host if request.client else "unknown"
    from app.core.redis import get_redis_client, RateLimiter
    from app.core.exceptions import RateLimitExceededError
    redis_client = get_redis_client()
    if redis_client:
        limiter = RateLimiter(redis_client)
        allowed, remaining, retry_after = await limiter.is_allowed(
            f"login:{ip_address}", max_requests=10, window_seconds=60,
        )
        if not allowed:
            raise RateLimitExceededError(
                message="Too many login attempts. Please try again later.",
                retry_after=retry_after,
            )

    service = AuthService(db)
    result = await service.authenticate_smart(data, tenant_id, ip_address)

    if isinstance(result, dict):
        status = result.get("status")
        if status == "tenant_redirect_required":
            return TenantRedirectRequired(
                tenant=TenantOption(**result["tenant"]),
            )
        return TenantSelectionRequired(
            tenants=[TenantOption(**t) for t in result["tenants"]],
            selection_token=result["selection_token"],
        )

    user, tokens = result
    return LoginResponse(
        tokens=tokens,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/select-tenant",
    response_model=LoginResponse,
    summary="Select tenant after login",
    description=(
        "Complete the login flow for a user with multiple tenants. "
        "Called after POST /auth/login returned "
        "status='tenant_selection_required'. No Authorization header "
        "needed -- the selection_token proves credentials were verified."
    ),
)
async def select_tenant(
    data: SelectTenantRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Finish multi-tenant login by choosing a specific tenant."""
    ip_address = request.client.host if request.client else None

    from app.core.redis import get_redis_client, RateLimiter
    from app.core.exceptions import RateLimitExceededError

    redis_client = get_redis_client()
    if redis_client:
        limiter = RateLimiter(redis_client)
        allowed, _, retry_after = await limiter.is_allowed(
            f"select_tenant:{ip_address}", max_requests=10, window_seconds=60,
        )
        if not allowed:
            raise RateLimitExceededError(
                message="Too many attempts. Please try again later.",
                retry_after=retry_after,
            )

    service = AuthService(db)
    user, tokens = await service.select_tenant(
        data.selection_token, data.tenant_id, ip_address,
    )
    return LoginResponse(
        tokens=tokens,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Refresh tokens",
    description="Get new access token using refresh token.",
)
async def refresh_tokens(
    data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Refresh access token using refresh token."""
    service = AuthService(db)
    return await service.refresh_tokens(data.refresh_token)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Request password reset",
    description="Send a password reset email. Always returns 204 regardless of whether the email exists (security).",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    tenant_id: UUID = Depends(get_tenant_from_header),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Request password reset email.
    
    Always returns 204 to prevent email enumeration.
    If the email exists in the tenant, a reset email is sent.
    """
    service = AuthService(db)
    await service.request_password_reset(data.email, tenant_id)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset password",
    description="Reset password using the token from the reset email.",
)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Reset password using a valid reset token."""
    service = AuthService(db)
    await service.reset_password(data.token, data.new_password)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Invalidate current session and revoke the access token.",
)
async def logout(
    token: TokenPayload = Depends(get_current_token),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Logout current user and revoke the access token.

    The token is added to a Redis blacklist with TTL matching token expiry.
    Any subsequent requests with this token will be rejected.
    """
    if token.jti:
        blacklist = await get_token_blacklist()
        if blacklist:
            await blacklist.add(token.jti, token.expires_in_seconds)
            logger.info("token_revoked", jti=token.jti[:8], user_id=str(token.user_id))
        else:
            logger.warning("logout_blacklist_unavailable", user_id=str(token.user_id))

    # Audit log: logout
    from app.core.audit import AuditService
    audit = AuditService(db)
    await audit.log(
        tenant_id=token.tenant_id,
        user_id=token.user_id,
        resource_type="auth",
        resource_id=token.user_id,
        action="logout",
    )
    await db.commit()


# ============================================================================
# Current User Routes
# ============================================================================


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_me(
    user: AdminUser = Depends(get_current_active_user),
) -> MeResponse:
    """Get current user information."""
    permissions: list[str] = []
    if user.role:
        permissions = [rp.permission.code for rp in user.role.role_permissions]

    return MeResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_superuser=user.is_superuser,
        force_password_change=user.force_password_change,
        role=RoleResponse.model_validate(user.role) if user.role else None,
        permissions=permissions,
    )


@router.get(
    "/me/tenants",
    response_model=MyTenantsResponse,
    summary="List my tenants",
    description=(
        "Return all organizations the current user has access to "
        "(same email, active, not deleted). Used by the tenant switcher."
    ),
)
async def get_my_tenants(
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> MyTenantsResponse:
    """List all tenants accessible to the current user."""
    service = AuthService(db)
    data = await service.get_user_tenants(user, current_tenant_id)
    return MyTenantsResponse(
        current_tenant_id=data["current_tenant_id"],
        tenants=[TenantAccessInfo(**t) for t in data["tenants"]],
    )


@router.post(
    "/switch-tenant",
    response_model=TokenPair,
    summary="Switch tenant",
    description=(
        "Switch the current user to a different organization. "
        "Returns new access_token + refresh_token scoped to the target tenant."
    ),
)
async def switch_tenant(
    data: SwitchTenantRequest,
    request: Request,
    token: TokenPayload = Depends(get_current_token),
    user: AdminUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """Switch to a different tenant and get new tokens.

    Rate-limited to 5 switches per minute per user.
    """
    from app.core.redis import get_redis_client, RateLimiter
    from app.core.exceptions import RateLimitExceededError

    redis_client = get_redis_client()
    if redis_client:
        limiter = RateLimiter(redis_client)
        allowed, _, retry_after = await limiter.is_allowed(
            f"switch_tenant:{user.id}", max_requests=5, window_seconds=60,
        )
        if not allowed:
            raise RateLimitExceededError(
                message="Too many tenant switches. Please try again later.",
                retry_after=retry_after,
            )

    ip_address = request.client.host if request.client else None
    service = AuthService(db)
    return await service.switch_tenant(
        user, data.tenant_id, ip_address,
        old_token_jti=token.jti,
        old_token_expires_in=token.expires_in_seconds,
    )


@router.get(
    "/me/features",
    response_model=FeatureCatalogResponse,
    summary="Get feature catalog",
    description="Get full feature catalog with enabled/disabled status for the current tenant. Used by frontend to build sidebar showing available, disabled, and requestable sections.",
)
async def get_my_features(
    locale: str = Query(default="en", description="Locale for titles/descriptions (en, ru)"),
    user: AdminUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FeatureCatalogResponse:
    """Get full feature catalog for current user's tenant.
    
    Returns all platform features with their enabled/disabled status,
    human-readable titles, descriptions, and whether the feature
    can be requested (when disabled).
    
    - Superusers and platform_owners: all_features_enabled=True, all features marked enabled
    - Regular users: actual feature flag status from database
    """
    from app.modules.tenants.models import AVAILABLE_FEATURES

    is_platform_owner = user.is_superuser or (user.role and user.role.name == "platform_owner")
    
    # Get enabled features from database
    service = FeatureFlagService(db)
    flags = await service.get_flags(user.tenant_id)
    enabled_set = {f.feature_name for f in flags if f.enabled}
    
    # Build catalog items
    use_ru = locale.startswith("ru")
    catalog_items: list[FeatureCatalogItem] = []
    
    for feature_name, meta in AVAILABLE_FEATURES.items():
        enabled = is_platform_owner or feature_name in enabled_set
        title = meta.get("title_ru" if use_ru else "title", feature_name)
        description = meta.get("description_ru" if use_ru else "description", "")
        
        catalog_items.append(FeatureCatalogItem(
            name=feature_name,
            title=title,
            description=description,
            category=meta.get("category", "other"),
            enabled=enabled,
            can_request=not enabled,
        ))
    
    return FeatureCatalogResponse(
        features=catalog_items,
        all_features_enabled=is_platform_owner,
        tenant_id=user.tenant_id,
    )


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Change current user's password.",
)
async def change_my_password(
    data: PasswordChange,
    user: AdminUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Change current user's password."""
    service = UserService(db)
    await service.change_password(user.id, user.tenant_id, data)


@router.post(
    "/me/avatar",
    response_model=MeResponse,
    summary="Upload my avatar",
    description="Upload or replace current user's avatar.",
)
async def upload_my_avatar(
    file: UploadFile = File(...),
    user: AdminUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Upload or replace current user's avatar.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    # Upload new avatar
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=user.tenant_id,
        folder="users",
        entity_id=user.id,
        old_image_url=user.avatar_url,
    )
    
    # Update user
    user.avatar_url = new_url
    await db.commit()
    await db.refresh(user, ["role"])
    
    permissions: list[str] = []
    if user.role:
        permissions = [rp.permission.code for rp in user.role.role_permissions]

    return MeResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_superuser=user.is_superuser,
        force_password_change=user.force_password_change,
        role=RoleResponse.model_validate(user.role) if user.role else None,
        permissions=permissions,
    )


@router.delete(
    "/me/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my avatar",
    description="Delete current user's avatar.",
)
async def delete_my_avatar(
    user: AdminUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete current user's avatar."""
    if user.avatar_url:
        await image_upload_service.delete_image(user.avatar_url)
        user.avatar_url = None
        await db.commit()


# ============================================================================
# User Management Routes (Admin)
# ============================================================================


def _resolve_effective_tenant(
    user: AdminUser,
    target_tenant_id: UUID | None,
    current_tenant_id: UUID,
) -> UUID:
    """Resolve effective tenant_id for cross-tenant operations.
    
    Platform owners and superusers can specify any tenant_id.
    Regular users are restricted to their own tenant.
    """
    if target_tenant_id is None:
        return current_tenant_id
    
    # Only platform_owner/superuser can cross-tenant
    if not user.is_superuser and not (user.role and user.role.name == "platform_owner"):
        raise PermissionDeniedError(
            required_permission="platform:read",
            message="You can only manage users in your own organization",
        )
    return target_tenant_id


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users in the tenant. Platform owner can specify tenant_id to list users of any organization.",
    dependencies=[Depends(PermissionChecker("users:read"))],
)
async def list_users(
    pagination: Pagination,
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant (platform owner only)"),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Search in email and name"),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List users in tenant."""
    effective_tenant_id = _resolve_effective_tenant(user, target_tenant_id, current_tenant_id)

    service = UserService(db)
    users, total = await service.list_users(
        tenant_id=effective_tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        is_active=is_active,
        search=search,
    )

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user. Platform owner can specify tenant_id to create users in any organization.",
    dependencies=[Depends(PermissionChecker("users:create"))],
)
async def create_user(
    data: UserCreate,
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant (platform owner only)"),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user in tenant."""
    effective_tenant_id = _resolve_effective_tenant(user, target_tenant_id, current_tenant_id)

    service = UserService(db, actor_id=user.id)
    new_user = await service.create(effective_tenant_id, data)
    return UserResponse.model_validate(new_user)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user",
    description="Get user by ID. Platform owner / superuser can view users from any organization (auto-resolved if tenant_id not specified).",
    dependencies=[Depends(PermissionChecker("users:read"))],
)
async def get_user(
    user_id: UUID,
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant (platform owner only)"),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user by ID.

    For superusers / platform owners: if tenant_id is not specified,
    first tries the current tenant, then falls back to a global lookup
    so that cross-tenant user profiles are always reachable.
    """
    effective_tenant_id = _resolve_effective_tenant(user, target_tenant_id, current_tenant_id)
    is_privileged = user.is_superuser or (
        user.role and user.role.name == "platform_owner"
    )

    service = UserService(db)

    try:
        found_user = await service.get_by_id(user_id, effective_tenant_id)
    except Exception:
        if is_privileged and target_tenant_id is None:
            found_user = await service.get_by_id_global(user_id)
        else:
            raise

    return UserResponse.model_validate(found_user)


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user. Platform owner can specify tenant_id to update users in any organization.",
    dependencies=[Depends(PermissionChecker("users:update"))],
)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant (platform owner only)"),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update user.

    For superusers / platform owners: if tenant_id is not specified,
    first tries the current tenant, then falls back to a global lookup
    so that cross-tenant user updates always work.
    """
    effective_tenant_id = _resolve_effective_tenant(user, target_tenant_id, current_tenant_id)
    is_privileged = user.is_superuser or (
        user.role and user.role.name == "platform_owner"
    )

    service = UserService(db, actor_id=user.id)
    try:
        updated_user = await service.update(user_id, effective_tenant_id, data)
    except NotFoundError:
        if is_privileged and target_tenant_id is None:
            found_user = await service.get_by_id_global(user_id)
            updated_user = await service.update(user_id, found_user.tenant_id, data)
        else:
            raise
    return UserResponse.model_validate(updated_user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Soft delete a user. Platform owner can specify tenant_id to delete users in any organization.",
    dependencies=[Depends(PermissionChecker("users:delete"))],
)
async def delete_user(
    user_id: UUID,
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant (platform owner only)"),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a user.

    For superusers / platform owners: if tenant_id is not specified,
    first tries the current tenant, then falls back to a global lookup.
    """
    effective_tenant_id = _resolve_effective_tenant(user, target_tenant_id, current_tenant_id)
    is_privileged = user.is_superuser or (
        user.role and user.role.name == "platform_owner"
    )

    service = UserService(db, actor_id=user.id)
    try:
        await service.soft_delete(user_id, effective_tenant_id)
    except NotFoundError:
        if is_privileged and target_tenant_id is None:
            found_user = await service.get_by_id_global(user_id)
            await service.soft_delete(user_id, found_user.tenant_id)
        else:
            raise


@router.post(
    "/users/{user_id}/avatar",
    response_model=UserResponse,
    summary="Upload user avatar",
    dependencies=[Depends(PermissionChecker("users:update"))],
)
async def upload_user_avatar(
    user_id: UUID,
    file: UploadFile = File(...),
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant (platform owner only)"),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Upload or replace avatar for user.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    effective_tenant_id = _resolve_effective_tenant(user, target_tenant_id, current_tenant_id)

    service = UserService(db)
    target_user = await service.get_by_id(user_id, effective_tenant_id)
    
    # Upload new avatar
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=effective_tenant_id,
        folder="users",
        entity_id=user_id,
        old_image_url=target_user.avatar_url,
    )
    
    # Update user
    target_user.avatar_url = new_url
    await db.commit()
    
    # Re-fetch user to avoid greenlet issues
    target_user = await service.get_by_id(user_id, effective_tenant_id)
    
    return UserResponse.model_validate(target_user)


@router.delete(
    "/users/{user_id}/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user avatar",
    dependencies=[Depends(PermissionChecker("users:update"))],
)
async def delete_user_avatar(
    user_id: UUID,
    target_tenant_id: UUID | None = Query(None, alias="tenant_id", description="Target tenant (platform owner only)"),
    user: AdminUser = Depends(get_current_active_user),
    current_tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete avatar from user."""
    effective_tenant_id = _resolve_effective_tenant(user, target_tenant_id, current_tenant_id)

    service = UserService(db)
    target_user = await service.get_by_id(user_id, effective_tenant_id)
    
    if target_user.avatar_url:
        await image_upload_service.delete_image(target_user.avatar_url)
        target_user.avatar_url = None
        await db.commit()


# ============================================================================
# Role & Permission Routes
# ============================================================================


@router.get(
    "/roles",
    response_model=RoleListResponse,
    summary="List roles",
    dependencies=[Depends(PermissionChecker("users:read"))],
)
async def list_roles(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RoleListResponse:
    """List all roles in tenant."""
    service = RoleService(db)
    roles = await service.list_roles(tenant_id)

    return RoleListResponse(
        items=[RoleResponse.model_validate(r) for r in roles],
        total=len(roles),
    )


@router.get(
    "/permissions",
    response_model=PermissionListResponse,
    summary="List permissions",
    dependencies=[Depends(PermissionChecker("users:read"))],
)
async def list_permissions(
    db: AsyncSession = Depends(get_db),
) -> PermissionListResponse:
    """List all available permissions."""
    service = RoleService(db)
    permissions = await service.list_permissions()

    return PermissionListResponse(
        items=[PermissionResponse.model_validate(p) for p in permissions],
        total=len(permissions),
    )


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create role",
    dependencies=[Depends(PermissionChecker("users:manage"))],
)
async def create_role(
    data: RoleCreate,
    user: AdminUser = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    """Create a new role with permissions."""
    service = RoleService(db, actor_id=user.id)
    role = await service.create_role(
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        permission_ids=data.permission_ids,
    )
    return RoleResponse.model_validate(role)


@router.patch(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Update role",
    dependencies=[Depends(PermissionChecker("users:manage"))],
)
async def update_role(
    role_id: UUID,
    data: RoleUpdate,
    user: AdminUser = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    """Update an existing role.

    Note: System roles cannot be modified.
    """
    service = RoleService(db, actor_id=user.id)
    role = await service.update_role(
        role_id=role_id,
        tenant_id=tenant_id,
        name=data.name,
        description=data.description,
        permission_ids=data.permission_ids,
    )
    return RoleResponse.model_validate(role)


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete role",
    dependencies=[Depends(PermissionChecker("users:manage"))],
)
async def delete_role(
    role_id: UUID,
    user: AdminUser = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a role.

    Note: System roles cannot be deleted.
    Note: Roles assigned to users cannot be deleted.
    """
    service = RoleService(db, actor_id=user.id)
    await service.delete_role(role_id, tenant_id)

