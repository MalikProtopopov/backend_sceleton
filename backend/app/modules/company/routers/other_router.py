"""Other company routes: practice areas, advantages, contacts."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Locale, PublicTenantId
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.company.mappers import (
    map_advantage_to_public_response,
    map_advantages_to_public_response,
    map_practice_areas_to_public_response,
)
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
    PracticeAreaCreate,
    PracticeAreaListResponse,
    PracticeAreaLocaleCreate,
    PracticeAreaLocaleResponse,
    PracticeAreaLocaleUpdate,
    PracticeAreaPublicResponse,
    PracticeAreaResponse,
    PracticeAreaUpdate,
)
from app.modules.company.service import (
    AdvantageService,
    ContactService,
    PracticeAreaService,
)

router = APIRouter()


# ============================================================================
# Public Routes - Practice Areas, Advantages, Contacts
# ============================================================================


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


# Practice Area Locales
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


# Advantage Locales
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


# Address Locales
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
