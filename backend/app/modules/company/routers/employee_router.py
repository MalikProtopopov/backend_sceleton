"""Employee routes for company module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Filtering, Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.company.mappers import (
    map_employee_to_public_response,
    map_employees_to_public_response,
)
from app.modules.company.schemas import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeLocaleCreate,
    EmployeeLocaleResponse,
    EmployeeLocaleUpdate,
    EmployeePublicResponse,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.modules.company.service import EmployeeService

router = APIRouter()


# ============================================================================
# Public Routes - Employees
# ============================================================================


@router.get(
    "/public/employees",
    response_model=list[EmployeePublicResponse],
    summary="List team members",
    tags=["Public - Company"],
)
async def list_employees_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> list[EmployeePublicResponse]:
    """List all published team members."""
    service = EmployeeService(db)
    employees = await service.list_published(tenant_id, locale.locale)
    return map_employees_to_public_response(employees, locale.locale)


@router.get(
    "/public/employees/{slug}",
    response_model=EmployeePublicResponse,
    summary="Get team member by slug",
    tags=["Public - Company"],
)
async def get_employee_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> EmployeePublicResponse:
    """Get a team member by slug."""
    service = EmployeeService(db)
    emp = await service.get_by_slug(slug, locale.locale, tenant_id)
    return map_employee_to_public_response(emp, locale.locale)


# ============================================================================
# Admin Routes - Employees
# ============================================================================


@router.get(
    "/admin/employees",
    response_model=EmployeeListResponse,
    summary="List employees (admin)",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:read"))],
)
async def list_employees_admin(
    pagination: Pagination,
    filtering: Filtering,
    search: str | None = Query(default=None, description="Search in name, position, email"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmployeeListResponse:
    """List all employees with pagination."""
    service = EmployeeService(db)
    employees, total = await service.list_employees(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        is_published=filtering.is_published,
        search=search,
    )

    return EmployeeListResponse(
        items=[EmployeeResponse.model_validate(e) for e in employees],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:create"))],
)
async def create_employee(
    data: EmployeeCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    """Create a new employee."""
    service = EmployeeService(db)
    created = await service.create(tenant_id, data)
    return EmployeeResponse.model_validate(created)


@router.get(
    "/admin/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get employee",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:read"))],
)
async def get_employee_admin(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    """Get employee by ID."""
    service = EmployeeService(db)
    emp = await service.get_by_id(employee_id, tenant_id)
    return EmployeeResponse.model_validate(emp)


@router.patch(
    "/admin/employees/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:update"))],
)
async def update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    """Update an employee."""
    service = EmployeeService(db)
    updated = await service.update(employee_id, tenant_id, data)
    return EmployeeResponse.model_validate(updated)


@router.delete(
    "/admin/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete employee",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:delete"))],
)
async def delete_employee(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an employee."""
    service = EmployeeService(db)
    await service.soft_delete(employee_id, tenant_id)


@router.post(
    "/admin/employees/{employee_id}/photo",
    response_model=EmployeeResponse,
    summary="Upload employee photo",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:update"))],
)
async def upload_employee_photo(
    employee_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    """Upload or replace photo for employee."""
    service = EmployeeService(db)
    emp = await service.get_by_id(employee_id, tenant_id)
    
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="employees",
        entity_id=employee_id,
        old_image_url=emp.photo_url,
    )
    
    emp.photo_url = new_url
    await db.commit()
    emp = await service.get_by_id(employee_id, tenant_id)
    
    return EmployeeResponse.model_validate(emp)


@router.delete(
    "/admin/employees/{employee_id}/photo",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete employee photo",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:update"))],
)
async def delete_employee_photo(
    employee_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete photo from employee."""
    service = EmployeeService(db)
    emp = await service.get_by_id(employee_id, tenant_id)
    
    if emp.photo_url:
        await image_upload_service.delete_image(emp.photo_url)
        emp.photo_url = None
        await db.commit()


# ============================================================================
# Admin Routes - Employee Locales
# ============================================================================


@router.post(
    "/admin/employees/{employee_id}/locales",
    response_model=EmployeeLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to employee",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:update"))],
)
async def create_employee_locale(
    employee_id: UUID,
    data: EmployeeLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmployeeLocaleResponse:
    """Add a new locale to an employee."""
    service = EmployeeService(db)
    locale = await service.create_locale(employee_id, tenant_id, data)
    return EmployeeLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/employees/{employee_id}/locales/{locale_id}",
    response_model=EmployeeLocaleResponse,
    summary="Update employee locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:update"))],
)
async def update_employee_locale(
    employee_id: UUID,
    locale_id: UUID,
    data: EmployeeLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> EmployeeLocaleResponse:
    """Update an employee locale."""
    service = EmployeeService(db)
    locale = await service.update_locale(locale_id, employee_id, tenant_id, data)
    return EmployeeLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/employees/{employee_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete employee locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("employees:update"))],
)
async def delete_employee_locale(
    employee_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from employee (minimum 1 locale required)."""
    service = EmployeeService(db)
    await service.delete_locale(locale_id, employee_id, tenant_id)
