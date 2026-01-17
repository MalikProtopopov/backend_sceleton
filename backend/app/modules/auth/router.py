"""API routes for authentication."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, get_tenant_from_header
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
    LoginRequest,
    LoginResponse,
    MeResponse,
    PasswordChange,
    PermissionListResponse,
    PermissionResponse,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
    TokenPair,
    TokenRefresh,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.modules.auth.service import AuthService, RoleService, UserService

router = APIRouter()


# ============================================================================
# Authentication Routes
# ============================================================================


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
    description="Authenticate user and receive JWT tokens. Requires X-Tenant-ID header.",
)
async def login(
    data: LoginRequest,
    request: Request,
    tenant_id: UUID = Depends(get_tenant_from_header),
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate user and return tokens."""
    service = AuthService(db)
    ip_address = request.client.host if request.client else None

    user, tokens = await service.authenticate(data, tenant_id, ip_address)

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
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Invalidate current session and revoke the access token.",
)
async def logout(
    token: TokenPayload = Depends(get_current_token),
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
        role=RoleResponse.model_validate(user.role) if user.role else None,
        permissions=permissions,
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


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List users",
    description="Get paginated list of users in the tenant.",
    dependencies=[Depends(PermissionChecker("users:read"))],
)
async def list_users(
    pagination: Pagination,
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Search in email and name"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List users in tenant."""
    service = UserService(db)
    users, total = await service.list_users(
        tenant_id=tenant_id,
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
    dependencies=[Depends(PermissionChecker("users:create"))],
)
async def create_user(
    data: UserCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a new user in tenant."""
    service = UserService(db)
    user = await service.create(tenant_id, data)
    return UserResponse.model_validate(user)


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user",
    dependencies=[Depends(PermissionChecker("users:read"))],
)
async def get_user(
    user_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get user by ID."""
    service = UserService(db)
    user = await service.get_by_id(user_id, tenant_id)
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    dependencies=[Depends(PermissionChecker("users:update"))],
)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update user."""
    service = UserService(db)
    user = await service.update(user_id, tenant_id, data)
    return UserResponse.model_validate(user)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    dependencies=[Depends(PermissionChecker("users:delete"))],
)
async def delete_user(
    user_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a user."""
    service = UserService(db)
    await service.soft_delete(user_id, tenant_id)


@router.post(
    "/users/{user_id}/avatar",
    response_model=UserResponse,
    summary="Upload user avatar",
    dependencies=[Depends(PermissionChecker("users:update"))],
)
async def upload_user_avatar(
    user_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Upload or replace avatar for user.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    service = UserService(db)
    user = await service.get_by_id(user_id, tenant_id)
    
    # Upload new avatar
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="users",
        entity_id=user_id,
        old_image_url=user.avatar_url,
    )
    
    # Update user
    user.avatar_url = new_url
    await db.commit()
    
    # Re-fetch user to avoid greenlet issues
    user = await service.get_by_id(user_id, tenant_id)
    
    return UserResponse.model_validate(user)


@router.delete(
    "/users/{user_id}/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user avatar",
    dependencies=[Depends(PermissionChecker("users:update"))],
)
async def delete_user_avatar(
    user_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete avatar from user."""
    service = UserService(db)
    user = await service.get_by_id(user_id, tenant_id)
    
    if user.avatar_url:
        await image_upload_service.delete_image(user.avatar_url)
        user.avatar_url = None
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
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    """Create a new role with permissions."""
    service = RoleService(db)
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
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    """Update an existing role.

    Note: System roles cannot be modified.
    """
    service = RoleService(db)
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
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a role.

    Note: System roles cannot be deleted.
    Note: Roles assigned to users cannot be deleted.
    """
    service = RoleService(db)
    await service.delete_role(role_id, tenant_id)

