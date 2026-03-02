"""Company module - practice area service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.modules.localization.helpers import (
    LocaleAlreadyExistsError,
    MinimumLocalesError,
    check_locale_exists,
    check_slug_unique,
    count_locales,
    get_locale_by_id,
    update_locale_fields,
)
from app.modules.company.models import (
    PracticeArea,
    PracticeAreaLocale,
)
from app.modules.company.schemas import (
    PracticeAreaCreate,
    PracticeAreaLocaleCreate,
    PracticeAreaLocaleUpdate,
    PracticeAreaUpdate,
)


class PracticeAreaService(BaseService[PracticeArea]):
    """Service for managing practice areas."""

    model = PracticeArea

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(PracticeArea.locales)]

    async def get_by_id(self, pa_id: UUID, tenant_id: UUID) -> PracticeArea:
        """Get practice area by ID."""
        return await self._get_by_id(pa_id, tenant_id)

    async def list_all(self, tenant_id: UUID) -> list[PracticeArea]:
        """List all practice areas for admin."""
        return await self._list_all(
            tenant_id,
            order_by=[PracticeArea.sort_order],
        )

    async def list_published(self, tenant_id: UUID, locale: str) -> list[PracticeArea]:
        """List published practice areas."""
        # Filter by locale at database level to ensure only items with the locale are returned
        stmt = (
            select(PracticeArea)
            .join(PracticeAreaLocale, PracticeArea.id == PracticeAreaLocale.practice_area_id)
            .where(PracticeArea.tenant_id == tenant_id)
            .where(PracticeArea.deleted_at.is_(None))
            .where(PracticeArea.is_published.is_(True))
            .where(PracticeAreaLocale.locale == locale)
            .options(selectinload(PracticeArea.locales))
            .order_by(PracticeArea.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    @transactional
    async def create(self, tenant_id: UUID, data: PracticeAreaCreate) -> PracticeArea:
        """Create a practice area."""
        pa = PracticeArea(
            tenant_id=tenant_id,
            icon=data.icon,
            is_published=data.is_published,
            sort_order=data.sort_order,
        )
        self.db.add(pa)
        await self.db.flush()

        for locale_data in data.locales:
            locale = PracticeAreaLocale(
                practice_area_id=pa.id,
                **locale_data.model_dump(),
            )
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(pa)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(pa, ["locales"])

        return pa

    @transactional
    async def update(self, pa_id: UUID, tenant_id: UUID, data: PracticeAreaUpdate) -> PracticeArea:
        """Update a practice area."""
        pa = await self.get_by_id(pa_id, tenant_id)
        pa.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(pa, field, value)

        await self.db.flush()
        await self.db.refresh(pa)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(pa, ["locales"])

        return pa

    @transactional
    async def soft_delete(self, pa_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a practice area."""
        await self._soft_delete(pa_id, tenant_id)

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, pa_id: UUID, tenant_id: UUID, data: PracticeAreaLocaleCreate
    ) -> PracticeAreaLocale:
        """Create a new locale for a practice area."""
        # Verify practice area exists
        await self.get_by_id(pa_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, PracticeAreaLocale, "practice_area_id", pa_id, data.locale
        ):
            raise LocaleAlreadyExistsError("PracticeArea", data.locale)

        # Check slug uniqueness
        await check_slug_unique(
            self.db, PracticeAreaLocale, PracticeArea, "practice_area_id",
            data.slug, data.locale, tenant_id
        )

        locale = PracticeAreaLocale(
            practice_area_id=pa_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, pa_id: UUID, tenant_id: UUID, data: PracticeAreaLocaleUpdate
    ) -> PracticeAreaLocale:
        """Update a practice area locale."""
        # Verify practice area exists
        await self.get_by_id(pa_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, PracticeAreaLocale, locale_id, "practice_area_id", pa_id, "PracticeArea"
        )

        # Check slug uniqueness if slug is being updated
        if data.slug and data.slug != locale.slug:
            await check_slug_unique(
                self.db, PracticeAreaLocale, PracticeArea, "practice_area_id",
                data.slug, locale.locale, tenant_id, exclude_locale_id=locale_id
            )

        # Update fields
        update_locale_fields(locale, data, ["title", "slug", "description"])

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, pa_id: UUID, tenant_id: UUID) -> None:
        """Delete a practice area locale."""
        # Verify practice area exists
        await self.get_by_id(pa_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, PracticeAreaLocale, "practice_area_id", pa_id)
        if locale_count <= 1:
            raise MinimumLocalesError("PracticeArea")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, PracticeAreaLocale, locale_id, "practice_area_id", pa_id, "PracticeArea"
        )
        await self.db.delete(locale)
        await self.db.flush()
