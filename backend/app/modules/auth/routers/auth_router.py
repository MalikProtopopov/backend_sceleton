"""Auth & session endpoints (login, refresh, logout, me, password reset, tenant switch)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_optional_tenant_from_header, get_tenant_from_header
from app.modules.media.upload_service import image_upload_service
from app.core.logging import get_logger
from app.core.redis import get_token_blacklist
from app.core.security import (
    TokenPayload,
    get_current_active_user,
    get_current_tenant_id,
    get_current_token,
)

logger = get_logger(__name__)
from app.modules.auth.models import AdminUser
from app.modules.auth.schemas import (
    FeatureCatalogItem,
    FeatureCatalogResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    MyTenantsResponse,
    PasswordChange,
    ResetPasswordRequest,
    RoleResponse,
    SelectTenantRequest,
    SwitchTenantRequest,
    TenantAccessInfo,
    TenantOption,
    TenantRedirectRequired,
    TenantSelectionRequired,
    TokenPair,
    TokenRefresh,
    UserResponse,
)
from app.modules.tenants.service import FeatureFlagService
from app.modules.auth.services import AuthService, UserService

router = APIRouter()


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
    request_origin = request.headers.get("origin") or request.headers.get("referer")
    result = await service.authenticate_smart(data, tenant_id, ip_address, request_origin)

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

    service = AuthService(db)
    await service.log_logout(token.tenant_id, token.user_id)


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
    
    service = UserService(db)
    updated_user = await service.update_avatar_url(user.id, user.tenant_id, new_url)
    
    permissions: list[str] = []
    if updated_user.role:
        permissions = [rp.permission.code for rp in updated_user.role.role_permissions]

    return MeResponse(
        id=updated_user.id,
        tenant_id=updated_user.tenant_id,
        email=updated_user.email,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        full_name=updated_user.full_name,
        avatar_url=updated_user.avatar_url,
        is_superuser=updated_user.is_superuser,
        force_password_change=updated_user.force_password_change,
        role=RoleResponse.model_validate(updated_user.role) if updated_user.role else None,
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
        service = UserService(db)
        await service.update_avatar_url(user.id, user.tenant_id, None)
