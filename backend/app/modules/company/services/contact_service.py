"""Company module - contact service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.core.locale_helpers import (
    LocaleAlreadyExistsError,
    MinimumLocalesError,
    check_locale_exists,
    count_locales,
    get_locale_by_id,
    update_locale_fields,
)
from app.modules.company.models import (
    Address,
    AddressLocale,
    Contact,
)
from app.modules.company.schemas import (
    AddressCreate,
    AddressLocaleCreate,
    AddressLocaleUpdate,
    AddressUpdate,
    ContactCreate,
    ContactUpdate,
)


class ContactService:
    """Service for managing contacts and addresses."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_contacts(self, tenant_id: UUID) -> tuple[list[Address], list[Contact]]:
        """Get all contacts and addresses for a tenant."""
        # Get addresses
        addr_stmt = (
            select(Address)
            .where(Address.tenant_id == tenant_id)
            .where(Address.deleted_at.is_(None))
            .options(selectinload(Address.locales))
            .order_by(Address.sort_order)
        )
        addr_result = await self.db.execute(addr_stmt)
        addresses = list(addr_result.scalars().all())

        # Get contacts
        contact_stmt = (
            select(Contact)
            .where(Contact.tenant_id == tenant_id)
            .where(Contact.deleted_at.is_(None))
            .order_by(Contact.sort_order)
        )
        contact_result = await self.db.execute(contact_stmt)
        contacts = list(contact_result.scalars().all())

        return addresses, contacts

    @transactional
    async def create_address(self, tenant_id: UUID, data: AddressCreate) -> Address:
        """Create an address."""
        address = Address(
            tenant_id=tenant_id,
            address_type=data.address_type,
            latitude=data.latitude,
            longitude=data.longitude,
            working_hours=data.working_hours,
            phone=data.phone,
            email=data.email,
            is_primary=data.is_primary,
            sort_order=data.sort_order,
        )
        self.db.add(address)
        await self.db.flush()

        for locale_data in data.locales:
            locale = AddressLocale(
                address_id=address.id,
                **locale_data.model_dump(),
            )
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(address)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(address, ["locales"])

        return address

    @transactional
    async def create_contact(self, tenant_id: UUID, data: ContactCreate) -> Contact:
        """Create a contact."""
        contact = Contact(tenant_id=tenant_id, **data.model_dump())
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    async def get_address_by_id(self, address_id: UUID, tenant_id: UUID) -> Address:
        """Get address by ID."""
        stmt = (
            select(Address)
            .where(Address.id == address_id)
            .where(Address.tenant_id == tenant_id)
            .where(Address.deleted_at.is_(None))
            .options(selectinload(Address.locales))
        )
        result = await self.db.execute(stmt)
        address = result.scalar_one_or_none()

        if not address:
            raise NotFoundError("Address", address_id)

        return address

    async def get_contact_by_id(self, contact_id: UUID, tenant_id: UUID) -> Contact:
        """Get contact by ID."""
        stmt = (
            select(Contact)
            .where(Contact.id == contact_id)
            .where(Contact.tenant_id == tenant_id)
            .where(Contact.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()

        if not contact:
            raise NotFoundError("Contact", contact_id)

        return contact

    async def list_addresses(self, tenant_id: UUID) -> list[Address]:
        """List all addresses."""
        stmt = (
            select(Address)
            .where(Address.tenant_id == tenant_id)
            .where(Address.deleted_at.is_(None))
            .options(selectinload(Address.locales))
            .order_by(Address.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_contacts(self, tenant_id: UUID) -> list[Contact]:
        """List all contacts."""
        stmt = (
            select(Contact)
            .where(Contact.tenant_id == tenant_id)
            .where(Contact.deleted_at.is_(None))
            .order_by(Contact.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def update_address(
        self, address_id: UUID, tenant_id: UUID, data: AddressUpdate
    ) -> Address:
        """Update an address."""
        address = await self.get_address_by_id(address_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(address, field, value)

        await self.db.flush()
        await self.db.refresh(address)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(address, ["locales"])

        return address

    @transactional
    async def update_contact(
        self, contact_id: UUID, tenant_id: UUID, data: ContactUpdate
    ) -> Contact:
        """Update a contact."""
        contact = await self.get_contact_by_id(contact_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(contact, field, value)

        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    @transactional
    async def soft_delete_address(self, address_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an address."""
        address = await self.get_address_by_id(address_id, tenant_id)
        address.soft_delete()
        await self.db.flush()

    @transactional
    async def soft_delete_contact(self, contact_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a contact."""
        contact = await self.get_contact_by_id(contact_id, tenant_id)
        contact.soft_delete()
        await self.db.flush()

    # ========== Address Locale Management ==========

    @transactional
    async def create_address_locale(
        self, address_id: UUID, tenant_id: UUID, data: AddressLocaleCreate
    ) -> AddressLocale:
        """Create a new locale for an address."""
        # Verify address exists
        await self.get_address_by_id(address_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, AddressLocale, "address_id", address_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Address", data.locale)

        locale = AddressLocale(
            address_id=address_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_address_locale(
        self, locale_id: UUID, address_id: UUID, tenant_id: UUID, data: AddressLocaleUpdate
    ) -> AddressLocale:
        """Update an address locale."""
        # Verify address exists
        await self.get_address_by_id(address_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, AddressLocale, locale_id, "address_id", address_id, "Address"
        )

        # Update fields
        update_locale_fields(
            locale, data, ["name", "country", "city", "street", "building", "postal_code"]
        )

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_address_locale(self, locale_id: UUID, address_id: UUID, tenant_id: UUID) -> None:
        """Delete an address locale."""
        # Verify address exists
        await self.get_address_by_id(address_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, AddressLocale, "address_id", address_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Address")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, AddressLocale, locale_id, "address_id", address_id, "Address"
        )
        await self.db.delete(locale)
        await self.db.flush()
