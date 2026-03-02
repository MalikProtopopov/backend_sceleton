"""Content module - FAQ service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.pagination import paginate_query
from app.modules.localization.helpers import (
    LocaleAlreadyExistsError,
    MinimumLocalesError,
    check_locale_exists,
    count_locales,
    get_locale_by_id,
    update_locale_fields,
)
from app.modules.content.models import (
    FAQ,
    FAQLocale,
)
from app.modules.content.schemas import (
    FAQCreate,
    FAQLocaleCreate,
    FAQLocaleUpdate,
    FAQUpdate,
)


class FAQService(BaseService[FAQ]):
    """Service for managing FAQ."""

    model = FAQ

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(FAQ.locales)]

    async def get_by_id(self, faq_id: UUID, tenant_id: UUID) -> FAQ:
        """Get FAQ by ID."""
        return await self._get_by_id(faq_id, tenant_id)

    async def list_faqs(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        category: str | None = None,
        is_published: bool | None = None,
    ) -> tuple[list[FAQ], int]:
        """List FAQs with pagination."""
        filters = []
        if category:
            filters.append(FAQ.category == category)
        if is_published is not None:
            filters.append(FAQ.is_published == is_published)

        base_query = self._build_base_query(tenant_id, filters=filters)

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=self._get_default_options(),
            order_by=[FAQ.category.nullsfirst(), FAQ.sort_order],
        )

    async def list_published(
        self, tenant_id: UUID, locale: str, category: str | None = None
    ) -> list[FAQ]:
        """List published FAQs for public API."""
        # Filter by locale at database level to ensure only FAQs with the locale are returned
        stmt = (
            select(FAQ)
            .join(FAQLocale, FAQ.id == FAQLocale.faq_id)
            .where(FAQ.tenant_id == tenant_id)
            .where(FAQ.deleted_at.is_(None))
            .where(FAQ.is_published.is_(True))
            .where(FAQLocale.locale == locale)
            .options(selectinload(FAQ.locales))
            .order_by(FAQ.category.nullsfirst(), FAQ.sort_order)
        )

        if category:
            stmt = stmt.where(FAQ.category == category)

        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    @transactional
    async def create(self, tenant_id: UUID, data: FAQCreate) -> FAQ:
        """Create a new FAQ."""
        faq = FAQ(
            tenant_id=tenant_id,
            category=data.category,
            is_published=data.is_published,
            sort_order=data.sort_order,
        )
        self.db.add(faq)
        await self.db.flush()

        for locale_data in data.locales:
            locale = FAQLocale(faq_id=faq.id, **locale_data.model_dump())
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(faq)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(faq, ["locales"])

        return faq

    @transactional
    async def update(self, faq_id: UUID, tenant_id: UUID, data: FAQUpdate) -> FAQ:
        """Update a FAQ."""
        faq = await self.get_by_id(faq_id, tenant_id)
        faq.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(faq, field, value)

        await self.db.flush()
        await self.db.refresh(faq)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(faq, ["locales"])

        return faq

    @transactional
    async def soft_delete(self, faq_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a FAQ."""
        await self._soft_delete(faq_id, tenant_id)

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, faq_id: UUID, tenant_id: UUID, data: FAQLocaleCreate
    ) -> FAQLocale:
        """Create a new locale for a FAQ."""
        # Verify FAQ exists
        await self.get_by_id(faq_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, FAQLocale, "faq_id", faq_id, data.locale
        ):
            raise LocaleAlreadyExistsError("FAQ", data.locale)

        locale = FAQLocale(
            faq_id=faq_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, faq_id: UUID, tenant_id: UUID, data: FAQLocaleUpdate
    ) -> FAQLocale:
        """Update a FAQ locale."""
        # Verify FAQ exists
        await self.get_by_id(faq_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, FAQLocale, locale_id, "faq_id", faq_id, "FAQ"
        )

        # Update fields
        update_locale_fields(locale, data, ["question", "answer"])

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, faq_id: UUID, tenant_id: UUID) -> None:
        """Delete a FAQ locale."""
        # Verify FAQ exists
        await self.get_by_id(faq_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, FAQLocale, "faq_id", faq_id)
        if locale_count <= 1:
            raise MinimumLocalesError("FAQ")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, FAQLocale, locale_id, "faq_id", faq_id, "FAQ"
        )
        await self.db.delete(locale)
        await self.db.flush()
