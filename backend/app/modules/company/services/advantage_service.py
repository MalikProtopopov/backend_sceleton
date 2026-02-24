"""Company module - advantage service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.locale_helpers import (
    LocaleAlreadyExistsError,
    MinimumLocalesError,
    check_locale_exists,
    count_locales,
    get_locale_by_id,
    update_locale_fields,
)
from app.modules.company.models import (
    Advantage,
    AdvantageLocale,
)
from app.modules.company.schemas import (
    AdvantageCreate,
    AdvantageLocaleCreate,
    AdvantageLocaleUpdate,
    AdvantageUpdate,
)


class AdvantageService(BaseService[Advantage]):
    """Service for managing advantages."""

    model = Advantage

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(Advantage.locales)]

    async def get_by_id(self, adv_id: UUID, tenant_id: UUID) -> Advantage:
        """Get advantage by ID."""
        return await self._get_by_id(adv_id, tenant_id)

    async def list_all(self, tenant_id: UUID) -> list[Advantage]:
        """List all advantages for admin."""
        return await self._list_all(
            tenant_id,
            order_by=[Advantage.sort_order],
        )

    async def list_published(self, tenant_id: UUID, locale: str) -> list[Advantage]:
        """List published advantages."""
        # Filter by locale at database level to ensure only items with the locale are returned
        stmt = (
            select(Advantage)
            .join(AdvantageLocale, Advantage.id == AdvantageLocale.advantage_id)
            .where(Advantage.tenant_id == tenant_id)
            .where(Advantage.deleted_at.is_(None))
            .where(Advantage.is_published.is_(True))
            .where(AdvantageLocale.locale == locale)
            .options(selectinload(Advantage.locales))
            .order_by(Advantage.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    @transactional
    async def create(self, tenant_id: UUID, data: AdvantageCreate) -> Advantage:
        """Create an advantage."""
        adv = Advantage(
            tenant_id=tenant_id,
            icon=data.icon,
            is_published=data.is_published,
            sort_order=data.sort_order,
        )
        self.db.add(adv)
        await self.db.flush()

        for locale_data in data.locales:
            locale = AdvantageLocale(
                advantage_id=adv.id,
                **locale_data.model_dump(),
            )
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(adv)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(adv, ["locales"])

        return adv

    @transactional
    async def update(self, adv_id: UUID, tenant_id: UUID, data: AdvantageUpdate) -> Advantage:
        """Update an advantage."""
        adv = await self.get_by_id(adv_id, tenant_id)
        adv.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(adv, field, value)

        await self.db.flush()
        await self.db.refresh(adv)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(adv, ["locales"])

        return adv

    @transactional
    async def soft_delete(self, adv_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an advantage."""
        await self._soft_delete(adv_id, tenant_id)

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, adv_id: UUID, tenant_id: UUID, data: AdvantageLocaleCreate
    ) -> AdvantageLocale:
        """Create a new locale for an advantage."""
        # Verify advantage exists
        await self.get_by_id(adv_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, AdvantageLocale, "advantage_id", adv_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Advantage", data.locale)

        locale = AdvantageLocale(
            advantage_id=adv_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, adv_id: UUID, tenant_id: UUID, data: AdvantageLocaleUpdate
    ) -> AdvantageLocale:
        """Update an advantage locale."""
        # Verify advantage exists
        await self.get_by_id(adv_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, AdvantageLocale, locale_id, "advantage_id", adv_id, "Advantage"
        )

        # Update fields
        update_locale_fields(locale, data, ["title", "description"])

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, adv_id: UUID, tenant_id: UUID) -> None:
        """Delete an advantage locale."""
        # Verify advantage exists
        await self.get_by_id(adv_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, AdvantageLocale, "advantage_id", adv_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Advantage")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, AdvantageLocale, locale_id, "advantage_id", adv_id, "Advantage"
        )
        await self.db.delete(locale)
        await self.db.flush()
