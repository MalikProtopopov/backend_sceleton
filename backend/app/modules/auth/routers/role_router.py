"""Role & permission management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    PermissionChecker,
    get_current_active_user,
    get_current_tenant_id,
)
from app.modules.auth.models import AdminUser
from app.modules.auth.schemas import (
    PermissionListResponse,
    PermissionResponse,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)
from app.modules.auth.services import RoleService

router = APIRouter()


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
