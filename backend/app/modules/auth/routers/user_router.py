"""User management endpoints (CRUD, avatars)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.image_upload import image_upload_service
from app.core.security import (
    PermissionChecker,
    get_current_active_user,
    get_current_tenant_id,
)
from app.modules.auth.models import AdminUser
from app.modules.auth.schemas import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.modules.auth.services import UserService

router = APIRouter()


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
    
    target_user = await service.update_avatar_url(user_id, effective_tenant_id, new_url)
    
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
        await service.update_avatar_url(user_id, effective_tenant_id, None)
