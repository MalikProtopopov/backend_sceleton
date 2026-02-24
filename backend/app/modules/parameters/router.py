"""API routes for parameters module."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination
from app.core.security import PermissionChecker, get_current_tenant_id
from app.middleware.feature_check import require_catalog
from app.modules.parameters.schemas import (
    ParameterCreate,
    ParameterListResponse,
    ParameterResponse,
    ParameterUpdate,
    ParameterValueCreate,
    ParameterValueResponse,
    ParameterValueUpdate,
    ProductCharacteristicCreate,
    ProductCharacteristicResponse,
)
from app.modules.parameters.service import (
    ParameterService,
    ProductCharacteristicService,
)

router = APIRouter()


# ============================================================================
# Parameter routes
# ============================================================================


@router.get(
    "/admin/parameters",
    response_model=ParameterListResponse,
    summary="List parameters",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_parameters(
    pagination: Pagination,
    search: str | None = Query(default=None, max_length=200),
    value_type: str | None = Query(default=None, alias="valueType"),
    scope: str | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ParameterListResponse:
    service = ParameterService(db)
    items, total = await service.list_parameters(
        tenant_id, page=pagination.page, page_size=pagination.page_size,
        search=search, value_type=value_type, scope=scope,
    )
    return ParameterListResponse(
        items=[ParameterResponse.model_validate(p) for p in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
    )


@router.get(
    "/admin/parameters/{parameter_id}",
    response_model=ParameterResponse,
    summary="Get parameter by ID",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def get_parameter(
    parameter_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ParameterResponse:
    service = ParameterService(db)
    param = await service.get_by_id(parameter_id, tenant_id)
    return ParameterResponse.model_validate(param)


@router.post(
    "/admin/parameters",
    response_model=ParameterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create parameter",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def create_parameter(
    data: ParameterCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ParameterResponse:
    service = ParameterService(db)
    param = await service.create(tenant_id, data)
    return ParameterResponse.model_validate(param)


@router.patch(
    "/admin/parameters/{parameter_id}",
    response_model=ParameterResponse,
    summary="Update parameter",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def update_parameter(
    parameter_id: UUID,
    data: ParameterUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ParameterResponse:
    service = ParameterService(db)
    param = await service.update(parameter_id, tenant_id, data)
    return ParameterResponse.model_validate(param)


@router.delete(
    "/admin/parameters/{parameter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate parameter (soft archive)",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def deactivate_parameter(
    parameter_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ParameterService(db)
    await service.deactivate(parameter_id, tenant_id)


# ============================================================================
# Parameter Value routes
# ============================================================================


@router.post(
    "/admin/parameters/{parameter_id}/values",
    response_model=ParameterValueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add value to enum parameter",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def create_parameter_value(
    parameter_id: UUID,
    data: ParameterValueCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ParameterValueResponse:
    service = ParameterService(db)
    pv = await service.create_value(parameter_id, tenant_id, data)
    return ParameterValueResponse.model_validate(pv)


@router.patch(
    "/admin/parameters/{parameter_id}/values/{value_id}",
    response_model=ParameterValueResponse,
    summary="Update parameter value",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def update_parameter_value(
    parameter_id: UUID,
    value_id: UUID,
    data: ParameterValueUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ParameterValueResponse:
    service = ParameterService(db)
    pv = await service.update_value(
        value_id, parameter_id, tenant_id,
        label=data.label, code=data.code,
        sort_order=data.sort_order, is_active=data.is_active,
    )
    return ParameterValueResponse.model_validate(pv)


@router.delete(
    "/admin/parameters/{parameter_id}/values/{value_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete parameter value",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def delete_parameter_value(
    parameter_id: UUID,
    value_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ParameterService(db)
    await service.delete_value(value_id, parameter_id, tenant_id)


# ============================================================================
# Product Characteristic routes
# ============================================================================


@router.get(
    "/admin/products/{product_id}/characteristics",
    response_model=list[ProductCharacteristicResponse],
    summary="List normalized characteristics for a product",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_product_characteristics(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ProductCharacteristicResponse]:
    service = ProductCharacteristicService(db)
    items = await service.list_for_product(product_id, tenant_id)
    return [ProductCharacteristicResponse.model_validate(c) for c in items]


@router.post(
    "/admin/products/{product_id}/characteristics",
    response_model=ProductCharacteristicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set product characteristic (upsert)",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def set_product_characteristic(
    product_id: UUID,
    data: ProductCharacteristicCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductCharacteristicResponse:
    service = ProductCharacteristicService(db)
    char = await service.set_characteristic(product_id, tenant_id, data)
    return ProductCharacteristicResponse.model_validate(char)


@router.delete(
    "/admin/products/{product_id}/characteristics/{parameter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product characteristic",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def delete_product_characteristic(
    product_id: UUID,
    parameter_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductCharacteristicService(db)
    await service.delete_characteristic(product_id, parameter_id, tenant_id)
