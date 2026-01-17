"""API routes for company module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Filtering, Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.company.schemas import (
    AddressCreate,
    AddressListResponse,
    AddressLocaleCreate,
    AddressLocaleResponse,
    AddressLocaleUpdate,
    AddressResponse,
    AddressUpdate,
    AdvantageCreate,
    AdvantageListResponse,
    AdvantageLocaleCreate,
    AdvantageLocaleResponse,
    AdvantageLocaleUpdate,
    AdvantagePublicResponse,
    AdvantageResponse,
    AdvantageUpdate,
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactsPublicResponse,
    ContactUpdate,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeLocaleCreate,
    EmployeeLocaleResponse,
    EmployeeLocaleUpdate,
    EmployeePublicResponse,
    EmployeeResponse,
    EmployeeUpdate,
    PracticeAreaCreate,
    PracticeAreaListResponse,
    PracticeAreaLocaleCreate,
    PracticeAreaLocaleResponse,
    PracticeAreaLocaleUpdate,
    PracticeAreaPublicResponse,
    PracticeAreaResponse,
    PracticeAreaUpdate,
    ServiceCreate,
    ServiceListResponse,
    ServiceLocaleCreate,
    ServiceLocaleResponse,
    ServiceLocaleUpdate,
    ServicePriceCreate,
    ServicePricePublic,
    ServicePriceResponse,
    ServicePriceUpdate,
    ServicePublicResponse,
    ServiceResponse,
    ServiceTagCreate,
    ServiceTagResponse,
    ServiceUpdate,
)
from app.modules.company.mappers import (
    map_advantage_to_public_response,
    map_advantages_to_public_response,
    map_employee_to_public_response,
    map_employees_to_public_response,
    map_practice_areas_to_public_response,
    map_service_to_public_response,
    map_services_to_public_response,
)
from app.modules.company.service import (
    AdvantageService,
    ContactService,
    EmployeeService,
    PracticeAreaService,
    ServiceService,
)

router = APIRouter()


# ============================================================================
# Public Routes
# ============================================================================


@router.get(
    "/public/services",
    response_model=list[ServicePublicResponse],
    summary="List published services",
    tags=["Public - Company"],
)
async def list_services_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> list[ServicePublicResponse]:
    """List all published services for public display."""
    service = ServiceService(db)
    services = await service.list_published(tenant_id, locale.locale)
    return map_services_to_public_response(services, locale.locale)


@router.get(
    "/public/services/{slug}",
    response_model=ServicePublicResponse,
    summary="Get service by slug",
    tags=["Public - Company"],
)
async def get_service_public(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> ServicePublicResponse:
    """Get a published service by slug."""
    service = ServiceService(db)
    svc = await service.get_by_slug(slug, locale.locale, tenant_id)
    return map_service_to_public_response(svc, locale.locale)


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


@router.get(
    "/public/practice-areas",
    response_model=list[PracticeAreaPublicResponse],
    summary="List practice areas",
    tags=["Public - Company"],
)
async def list_practice_areas_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> list[PracticeAreaPublicResponse]:
    """List all published practice areas."""
    service = PracticeAreaService(db)
    areas = await service.list_published(tenant_id, locale.locale)
    return map_practice_areas_to_public_response(areas, locale.locale)


@router.get(
    "/public/advantages",
    response_model=list[AdvantagePublicResponse],
    summary="List company advantages",
    tags=["Public - Company"],
)
async def list_advantages_public(
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> list[AdvantagePublicResponse]:
    """List all published advantages."""
    service = AdvantageService(db)
    advantages = await service.list_published(tenant_id, locale.locale)
    return map_advantages_to_public_response(advantages, locale.locale)


@router.get(
    "/public/contacts",
    response_model=ContactsPublicResponse,
    summary="Get contact information",
    tags=["Public - Company"],
)
async def get_contacts_public(
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> ContactsPublicResponse:
    """Get all contact information."""
    service = ContactService(db)
    addresses, contacts = await service.get_contacts(tenant_id)

    return ContactsPublicResponse(
        addresses=[AddressResponse.model_validate(a) for a in addresses],
        contacts=[ContactResponse.model_validate(c) for c in contacts],
    )


# ============================================================================
# Admin Routes - Services
# ============================================================================


@router.get(
    "/admin/services",
    response_model=ServiceListResponse,
    summary="List services (admin)",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def list_services_admin(
    pagination: Pagination,
    filtering: Filtering,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceListResponse:
    """List all services with pagination."""
    service = ServiceService(db)
    services, total = await service.list_services(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        is_published=filtering.is_published,
    )

    return ServiceListResponse(
        items=[ServiceResponse.model_validate(s) for s in services],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/services",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:create"))],
)
async def create_service(
    data: ServiceCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Create a new service."""
    service = ServiceService(db)
    created = await service.create(tenant_id, data)
    return ServiceResponse.model_validate(created)


@router.get(
    "/admin/services/{service_id}",
    response_model=ServiceResponse,
    summary="Get service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def get_service_admin(
    service_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Get service by ID."""
    service = ServiceService(db)
    svc = await service.get_by_id(service_id, tenant_id)
    return ServiceResponse.model_validate(svc)


@router.patch(
    "/admin/services/{service_id}",
    response_model=ServiceResponse,
    summary="Update service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service(
    service_id: UUID,
    data: ServiceUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Update a service."""
    service = ServiceService(db)
    await service.update(service_id, tenant_id, data)
    # Re-fetch service with all relationships to avoid greenlet issues
    updated = await service.get_by_id(service_id, tenant_id)
    return ServiceResponse.model_validate(updated)


@router.delete(
    "/admin/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:delete"))],
)
async def delete_service(
    service_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a service."""
    service = ServiceService(db)
    await service.soft_delete(service_id, tenant_id)


@router.post(
    "/admin/services/{service_id}/image",
    response_model=ServiceResponse,
    summary="Upload service image",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def upload_service_image(
    service_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceResponse:
    """Upload or replace image for service.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    service = ServiceService(db)
    svc = await service.get_by_id(service_id, tenant_id)
    
    # Upload new image
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="services",
        entity_id=service_id,
        old_image_url=svc.image_url,
    )
    
    # Update service
    svc.image_url = new_url
    await db.commit()
    
    # Re-fetch service with all relationships to avoid greenlet issues
    svc = await service.get_by_id(service_id, tenant_id)
    
    return ServiceResponse.model_validate(svc)


@router.delete(
    "/admin/services/{service_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service image",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_image(
    service_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete image from service."""
    service = ServiceService(db)
    svc = await service.get_by_id(service_id, tenant_id)
    
    if svc.image_url:
        await image_upload_service.delete_image(svc.image_url)
        svc.image_url = None
        await db.commit()


@router.post(
    "/admin/services/{service_id}/prices",
    response_model=ServicePriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add price to service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_service_price(
    service_id: UUID,
    data: ServicePriceCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServicePriceResponse:
    """Add a price for a service in a specific locale and currency."""
    service = ServiceService(db)
    price = await service.create_price(service_id, tenant_id, data)
    return ServicePriceResponse.model_validate(price)


@router.patch(
    "/admin/services/{service_id}/prices/{price_id}",
    response_model=ServicePriceResponse,
    summary="Update service price",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service_price(
    service_id: UUID,
    price_id: UUID,
    data: ServicePriceUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServicePriceResponse:
    """Update a service price."""
    service = ServiceService(db)
    price = await service.update_price(price_id, service_id, tenant_id, data)
    return ServicePriceResponse.model_validate(price)


@router.delete(
    "/admin/services/{service_id}/prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service price",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_price(
    service_id: UUID,
    price_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a price from service."""
    service = ServiceService(db)
    await service.delete_price(price_id, service_id, tenant_id)


@router.post(
    "/admin/services/{service_id}/tags",
    response_model=ServiceTagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add tag to service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_service_tag(
    service_id: UUID,
    data: ServiceTagCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceTagResponse:
    """Add a tag to a service in a specific locale."""
    service = ServiceService(db)
    tag = await service.create_tag(service_id, tenant_id, data)
    return ServiceTagResponse.model_validate(tag)


@router.patch(
    "/admin/services/{service_id}/tags/{tag_id}",
    response_model=ServiceTagResponse,
    summary="Update service tag",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service_tag(
    service_id: UUID,
    tag_id: UUID,
    data: ServiceTagCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceTagResponse:
    """Update a service tag."""
    service = ServiceService(db)
    tag = await service.update_tag(tag_id, service_id, tenant_id, data)
    return ServiceTagResponse.model_validate(tag)


@router.delete(
    "/admin/services/{service_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service tag",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_tag(
    service_id: UUID,
    tag_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tag from service."""
    service = ServiceService(db)
    await service.delete_tag(tag_id, service_id, tenant_id)


# ============================================================================
# Admin Routes - Service Locales
# ============================================================================


@router.post(
    "/admin/services/{service_id}/locales",
    response_model=ServiceLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to service",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_service_locale(
    service_id: UUID,
    data: ServiceLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceLocaleResponse:
    """Add a new locale to a service."""
    service = ServiceService(db)
    locale = await service.create_locale(service_id, tenant_id, data)
    return ServiceLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/services/{service_id}/locales/{locale_id}",
    response_model=ServiceLocaleResponse,
    summary="Update service locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_service_locale(
    service_id: UUID,
    locale_id: UUID,
    data: ServiceLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ServiceLocaleResponse:
    """Update a service locale."""
    service = ServiceService(db)
    locale = await service.update_locale(locale_id, service_id, tenant_id, data)
    return ServiceLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/services/{service_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete service locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_service_locale(
    service_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from service (minimum 1 locale required)."""
    service = ServiceService(db)
    await service.delete_locale(locale_id, service_id, tenant_id)


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
    """Upload or replace photo for employee.
    
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum size: 10MB
    """
    service = EmployeeService(db)
    emp = await service.get_by_id(employee_id, tenant_id)
    
    # Upload new image
    new_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="employees",
        entity_id=employee_id,
        old_image_url=emp.photo_url,
    )
    
    # Update employee
    emp.photo_url = new_url
    await db.commit()
    
    # Re-fetch employee with all relationships to avoid greenlet issues
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


# ============================================================================
# Admin Routes - Practice Areas
# ============================================================================


@router.get(
    "/admin/practice-areas",
    response_model=PracticeAreaListResponse,
    summary="List practice areas (admin)",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def list_practice_areas_admin(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PracticeAreaListResponse:
    """List all practice areas."""
    service = PracticeAreaService(db)
    items = await service.list_all(tenant_id)
    return PracticeAreaListResponse(
        items=[PracticeAreaResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post(
    "/admin/practice-areas",
    response_model=PracticeAreaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create practice area",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:create"))],
)
async def create_practice_area(
    data: PracticeAreaCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PracticeAreaResponse:
    """Create a new practice area."""
    service = PracticeAreaService(db)
    created = await service.create(tenant_id, data)
    return PracticeAreaResponse.model_validate(created)


@router.get(
    "/admin/practice-areas/{pa_id}",
    response_model=PracticeAreaResponse,
    summary="Get practice area",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def get_practice_area(
    pa_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PracticeAreaResponse:
    """Get practice area by ID."""
    service = PracticeAreaService(db)
    pa = await service.get_by_id(pa_id, tenant_id)
    return PracticeAreaResponse.model_validate(pa)


@router.patch(
    "/admin/practice-areas/{pa_id}",
    response_model=PracticeAreaResponse,
    summary="Update practice area",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_practice_area(
    pa_id: UUID,
    data: PracticeAreaUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PracticeAreaResponse:
    """Update a practice area."""
    service = PracticeAreaService(db)
    updated = await service.update(pa_id, tenant_id, data)
    return PracticeAreaResponse.model_validate(updated)


@router.delete(
    "/admin/practice-areas/{pa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete practice area",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:delete"))],
)
async def delete_practice_area(
    pa_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a practice area."""
    service = PracticeAreaService(db)
    await service.soft_delete(pa_id, tenant_id)


# ============================================================================
# Admin Routes - Practice Area Locales
# ============================================================================


@router.post(
    "/admin/practice-areas/{pa_id}/locales",
    response_model=PracticeAreaLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to practice area",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_practice_area_locale(
    pa_id: UUID,
    data: PracticeAreaLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PracticeAreaLocaleResponse:
    """Add a new locale to a practice area."""
    service = PracticeAreaService(db)
    locale = await service.create_locale(pa_id, tenant_id, data)
    return PracticeAreaLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/practice-areas/{pa_id}/locales/{locale_id}",
    response_model=PracticeAreaLocaleResponse,
    summary="Update practice area locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_practice_area_locale(
    pa_id: UUID,
    locale_id: UUID,
    data: PracticeAreaLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PracticeAreaLocaleResponse:
    """Update a practice area locale."""
    service = PracticeAreaService(db)
    locale = await service.update_locale(locale_id, pa_id, tenant_id, data)
    return PracticeAreaLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/practice-areas/{pa_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete practice area locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_practice_area_locale(
    pa_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from practice area (minimum 1 locale required)."""
    service = PracticeAreaService(db)
    await service.delete_locale(locale_id, pa_id, tenant_id)


# ============================================================================
# Admin Routes - Advantages
# ============================================================================


@router.get(
    "/admin/advantages",
    response_model=AdvantageListResponse,
    summary="List advantages (admin)",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def list_advantages_admin(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AdvantageListResponse:
    """List all advantages."""
    service = AdvantageService(db)
    items = await service.list_all(tenant_id)
    return AdvantageListResponse(
        items=[AdvantageResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post(
    "/admin/advantages",
    response_model=AdvantageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create advantage",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:create"))],
)
async def create_advantage(
    data: AdvantageCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AdvantageResponse:
    """Create a new advantage."""
    service = AdvantageService(db)
    created = await service.create(tenant_id, data)
    return AdvantageResponse.model_validate(created)


@router.get(
    "/admin/advantages/{adv_id}",
    response_model=AdvantageResponse,
    summary="Get advantage",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:read"))],
)
async def get_advantage(
    adv_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AdvantageResponse:
    """Get advantage by ID."""
    service = AdvantageService(db)
    adv = await service.get_by_id(adv_id, tenant_id)
    return AdvantageResponse.model_validate(adv)


@router.patch(
    "/admin/advantages/{adv_id}",
    response_model=AdvantageResponse,
    summary="Update advantage",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_advantage(
    adv_id: UUID,
    data: AdvantageUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AdvantageResponse:
    """Update an advantage."""
    service = AdvantageService(db)
    updated = await service.update(adv_id, tenant_id, data)
    return AdvantageResponse.model_validate(updated)


@router.delete(
    "/admin/advantages/{adv_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete advantage",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:delete"))],
)
async def delete_advantage(
    adv_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an advantage."""
    service = AdvantageService(db)
    await service.soft_delete(adv_id, tenant_id)


# ============================================================================
# Admin Routes - Advantage Locales
# ============================================================================


@router.post(
    "/admin/advantages/{adv_id}/locales",
    response_model=AdvantageLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to advantage",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def create_advantage_locale(
    adv_id: UUID,
    data: AdvantageLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AdvantageLocaleResponse:
    """Add a new locale to an advantage."""
    service = AdvantageService(db)
    locale = await service.create_locale(adv_id, tenant_id, data)
    return AdvantageLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/advantages/{adv_id}/locales/{locale_id}",
    response_model=AdvantageLocaleResponse,
    summary="Update advantage locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def update_advantage_locale(
    adv_id: UUID,
    locale_id: UUID,
    data: AdvantageLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AdvantageLocaleResponse:
    """Update an advantage locale."""
    service = AdvantageService(db)
    locale = await service.update_locale(locale_id, adv_id, tenant_id, data)
    return AdvantageLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/advantages/{adv_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete advantage locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("services:update"))],
)
async def delete_advantage_locale(
    adv_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from advantage (minimum 1 locale required)."""
    service = AdvantageService(db)
    await service.delete_locale(locale_id, adv_id, tenant_id)


# ============================================================================
# Admin Routes - Addresses
# ============================================================================


@router.get(
    "/admin/addresses",
    response_model=AddressListResponse,
    summary="List addresses (admin)",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:read"))],
)
async def list_addresses_admin(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AddressListResponse:
    """List all addresses."""
    service = ContactService(db)
    items = await service.list_addresses(tenant_id)
    return AddressListResponse(
        items=[AddressResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post(
    "/admin/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create address",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def create_address(
    data: AddressCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    """Create a new address."""
    service = ContactService(db)
    created = await service.create_address(tenant_id, data)
    return AddressResponse.model_validate(created)


@router.get(
    "/admin/addresses/{address_id}",
    response_model=AddressResponse,
    summary="Get address",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:read"))],
)
async def get_address(
    address_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    """Get address by ID."""
    service = ContactService(db)
    address = await service.get_address_by_id(address_id, tenant_id)
    return AddressResponse.model_validate(address)


@router.patch(
    "/admin/addresses/{address_id}",
    response_model=AddressResponse,
    summary="Update address",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def update_address(
    address_id: UUID,
    data: AddressUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AddressResponse:
    """Update an address."""
    service = ContactService(db)
    updated = await service.update_address(address_id, tenant_id, data)
    return AddressResponse.model_validate(updated)


@router.delete(
    "/admin/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete address",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def delete_address(
    address_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an address."""
    service = ContactService(db)
    await service.soft_delete_address(address_id, tenant_id)


# ============================================================================
# Admin Routes - Address Locales
# ============================================================================


@router.post(
    "/admin/addresses/{address_id}/locales",
    response_model=AddressLocaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add locale to address",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def create_address_locale(
    address_id: UUID,
    data: AddressLocaleCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AddressLocaleResponse:
    """Add a new locale to an address."""
    service = ContactService(db)
    locale = await service.create_address_locale(address_id, tenant_id, data)
    return AddressLocaleResponse.model_validate(locale)


@router.patch(
    "/admin/addresses/{address_id}/locales/{locale_id}",
    response_model=AddressLocaleResponse,
    summary="Update address locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def update_address_locale(
    address_id: UUID,
    locale_id: UUID,
    data: AddressLocaleUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> AddressLocaleResponse:
    """Update an address locale."""
    service = ContactService(db)
    locale = await service.update_address_locale(locale_id, address_id, tenant_id, data)
    return AddressLocaleResponse.model_validate(locale)


@router.delete(
    "/admin/addresses/{address_id}/locales/{locale_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete address locale",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def delete_address_locale(
    address_id: UUID,
    locale_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a locale from address (minimum 1 locale required)."""
    service = ContactService(db)
    await service.delete_address_locale(locale_id, address_id, tenant_id)


# ============================================================================
# Admin Routes - Contacts
# ============================================================================


@router.get(
    "/admin/contacts",
    response_model=ContactListResponse,
    summary="List contacts (admin)",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:read"))],
)
async def list_contacts_admin(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContactListResponse:
    """List all contacts."""
    service = ContactService(db)
    items = await service.list_contacts(tenant_id)
    return ContactListResponse(
        items=[ContactResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post(
    "/admin/contacts",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create contact",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def create_contact(
    data: ContactCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Create a new contact."""
    service = ContactService(db)
    created = await service.create_contact(tenant_id, data)
    return ContactResponse.model_validate(created)


@router.get(
    "/admin/contacts/{contact_id}",
    response_model=ContactResponse,
    summary="Get contact",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:read"))],
)
async def get_contact(
    contact_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Get contact by ID."""
    service = ContactService(db)
    contact = await service.get_contact_by_id(contact_id, tenant_id)
    return ContactResponse.model_validate(contact)


@router.patch(
    "/admin/contacts/{contact_id}",
    response_model=ContactResponse,
    summary="Update contact",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Update a contact."""
    service = ContactService(db)
    updated = await service.update_contact(contact_id, tenant_id, data)
    return ContactResponse.model_validate(updated)


@router.delete(
    "/admin/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete contact",
    tags=["Admin - Company"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def delete_contact(
    contact_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a contact."""
    service = ContactService(db)
    await service.soft_delete_contact(contact_id, tenant_id)

