"""Content module - case service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService, update_many_to_many
from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.core.locale_helpers import (
    LocaleAlreadyExistsError,
    MinimumLocalesError,
    check_locale_exists,
    check_slug_unique,
    count_locales,
    get_locale_by_id,
    update_locale_fields,
)
from app.modules.content.models import (
    ArticleStatus,
    Case,
    CaseContact,
    CaseLocale,
    CaseServiceLink,
)
from app.modules.content.schemas import (
    CaseContactCreate,
    CaseContactUpdate,
    CaseCreate,
    CaseLocaleCreate,
    CaseLocaleUpdate,
    CaseUpdate,
)


class CaseService(BaseService[Case]):
    """Service for managing cases (portfolio / case studies)."""

    model = Case

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [
            selectinload(Case.locales),
            selectinload(Case.services).selectinload(CaseServiceLink.service),
        ]

    async def get_by_id(self, case_id: UUID, tenant_id: UUID) -> Case:
        """Get case by ID."""
        return await self._get_by_id(case_id, tenant_id)

    async def get_by_slug(self, slug: str, locale: str, tenant_id: UUID) -> Case:
        """Get published case by slug."""
        stmt = (
            select(Case)
            .join(CaseLocale)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == ArticleStatus.PUBLISHED.value)
            .where(CaseLocale.locale == locale)
            .where(CaseLocale.slug == slug)
            .options(
                selectinload(Case.locales),
                selectinload(Case.services).selectinload(CaseServiceLink.service),
            )
        )
        result = await self.db.execute(stmt)
        case = result.scalar_one_or_none()

        if not case:
            raise NotFoundError("Case", slug)

        return case

    async def list_cases(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        is_featured: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Case], int]:
        """List cases with pagination and filters."""
        base_query = (
            select(Case)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
        )

        if status:
            base_query = base_query.where(Case.status == status)

        if is_featured is not None:
            base_query = base_query.where(Case.is_featured == is_featured)

        if search:
            # Search in client_name and locales title
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(CaseLocale).where(
                (Case.client_name.ilike(search_pattern)) |
                (CaseLocale.title.ilike(search_pattern))
            ).distinct()

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(
                selectinload(Case.locales),
                selectinload(Case.services).selectinload(CaseServiceLink.service),
            )
            .order_by(Case.sort_order, Case.published_at.desc().nullsfirst())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        cases = list(result.scalars().unique().all())

        return cases, total

    async def list_published(
        self,
        tenant_id: UUID,
        locale: str,
        page: int = 1,
        page_size: int = 20,
        is_featured: bool | None = None,
    ) -> tuple[list[Case], int]:
        """List published cases for public API."""
        # Filter by locale at database level to ensure correct pagination
        base_query = (
            select(Case)
            .join(CaseLocale, Case.id == CaseLocale.case_id)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == ArticleStatus.PUBLISHED.value)
            .where(CaseLocale.locale == locale)
        )

        if is_featured is not None:
            base_query = base_query.where(Case.is_featured == is_featured)

        # Count - reflects items with requested locale
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(
                selectinload(Case.locales),
                selectinload(Case.services).selectinload(CaseServiceLink.service),
            )
            .order_by(Case.sort_order, Case.published_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        cases = list(result.scalars().unique().all())

        return cases, total

    @transactional
    async def create(self, tenant_id: UUID, data: CaseCreate) -> Case:
        """Create a new case."""
        # Check slug uniqueness
        for locale_data in data.locales:
            await check_slug_unique(
                self.db, CaseLocale, Case, "case_id",
                locale_data.slug, locale_data.locale, tenant_id
            )

        # Create case (cover_image_url is set via separate endpoint)
        case = Case(
            tenant_id=tenant_id,
            status=data.status.value,
            client_name=data.client_name,
            project_year=data.project_year,
            project_duration=data.project_duration,
            is_featured=data.is_featured,
            sort_order=data.sort_order,
        )

        if data.status.value == ArticleStatus.PUBLISHED.value:
            case.published_at = datetime.now(UTC)

        self.db.add(case)
        await self.db.flush()

        # Create locales
        for locale_data in data.locales:
            locale = CaseLocale(case_id=case.id, **locale_data.model_dump())
            self.db.add(locale)

        # Add service links
        for service_id in data.service_ids:
            link = CaseServiceLink(case_id=case.id, service_id=service_id)
            self.db.add(link)

        await self.db.flush()
        # Re-fetch with proper eager loading for nested relations
        return await self.get_by_id(case.id, tenant_id)

    @transactional
    async def update(self, case_id: UUID, tenant_id: UUID, data: CaseUpdate) -> Case:
        """Update a case."""
        case = await self.get_by_id(case_id, tenant_id)
        case.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version", "service_ids"})

        # Handle status change to published
        if "status" in update_data:
            new_status = update_data["status"]
            if hasattr(new_status, "value"):
                update_data["status"] = new_status.value
            if new_status == ArticleStatus.PUBLISHED and case.status != ArticleStatus.PUBLISHED.value:
                case.published_at = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(case, field, value)

        # Update service links if provided
        if data.service_ids is not None:
            await update_many_to_many(
                self.db,
                case,
                "services",
                data.service_ids,
                CaseServiceLink,
                "case_id",
                "service_id",
            )

        await self.db.flush()
        # Re-fetch with proper eager loading for nested relations
        return await self.get_by_id(case_id, tenant_id)

    @transactional
    async def publish(self, case_id: UUID, tenant_id: UUID) -> Case:
        """Publish a case."""
        case = await self.get_by_id(case_id, tenant_id)
        case.status = ArticleStatus.PUBLISHED.value
        if not case.published_at:
            case.published_at = datetime.now(UTC)
        await self.db.flush()
        # Re-fetch with proper eager loading for nested relations
        return await self.get_by_id(case_id, tenant_id)

    @transactional
    async def unpublish(self, case_id: UUID, tenant_id: UUID) -> Case:
        """Unpublish a case (move to draft)."""
        case = await self.get_by_id(case_id, tenant_id)
        case.status = ArticleStatus.DRAFT.value
        await self.db.flush()
        # Re-fetch with proper eager loading for nested relations
        return await self.get_by_id(case_id, tenant_id)

    @transactional
    async def update_cover_image_url(
        self, case_id: UUID, tenant_id: UUID, url: str | None
    ) -> "Case":
        """Update or clear the case cover image URL."""
        case = await self.get_by_id(case_id, tenant_id)
        case.cover_image_url = url
        await self.db.flush()
        await self.db.refresh(case)
        await self.db.refresh(case, ["locales", "services"])
        return case

    @transactional
    async def soft_delete(self, case_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a case."""
        await self._soft_delete(case_id, tenant_id)

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, case_id: UUID, tenant_id: UUID, data: CaseLocaleCreate
    ) -> CaseLocale:
        """Create a new locale for a case."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, CaseLocale, "case_id", case_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Case", data.locale)

        # Check slug uniqueness
        await check_slug_unique(
            self.db, CaseLocale, Case, "case_id",
            data.slug, data.locale, tenant_id
        )

        locale = CaseLocale(
            case_id=case_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, case_id: UUID, tenant_id: UUID, data: CaseLocaleUpdate
    ) -> CaseLocale:
        """Update a case locale."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, CaseLocale, locale_id, "case_id", case_id, "Case"
        )

        # Check slug uniqueness if slug is being updated
        if data.slug and data.slug != locale.slug:
            await check_slug_unique(
                self.db, CaseLocale, Case, "case_id",
                data.slug, locale.locale, tenant_id, exclude_locale_id=locale_id
            )

        # Update fields
        update_locale_fields(
            locale, data,
            ["title", "slug", "excerpt", "description", "results", "meta_title", "meta_description"]
        )

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, case_id: UUID, tenant_id: UUID) -> None:
        """Delete a case locale."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, CaseLocale, "case_id", case_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Case")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, CaseLocale, locale_id, "case_id", case_id, "Case"
        )
        await self.db.delete(locale)
        await self.db.flush()

    # ========== Contact Management ==========

    @transactional
    async def add_contact(
        self, case_id: UUID, tenant_id: UUID, data: CaseContactCreate
    ) -> CaseContact:
        """Add a contact to a case."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        contact = CaseContact(
            case_id=case_id,
            contact_type=data.contact_type,
            value=data.value,
            sort_order=data.sort_order,
        )
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    @transactional
    async def update_contact(
        self, contact_id: UUID, case_id: UUID, tenant_id: UUID, data: CaseContactUpdate
    ) -> CaseContact:
        """Update a case contact."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Get contact
        stmt = select(CaseContact).where(
            CaseContact.id == contact_id,
            CaseContact.case_id == case_id,
        )
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()

        if not contact:
            raise NotFoundError("CaseContact", contact_id)

        # Update fields
        if data.contact_type is not None:
            contact.contact_type = data.contact_type
        if data.value is not None:
            contact.value = data.value
        if data.sort_order is not None:
            contact.sort_order = data.sort_order

        await self.db.flush()
        await self.db.refresh(contact)

        return contact

    @transactional
    async def delete_contact(
        self, contact_id: UUID, case_id: UUID, tenant_id: UUID
    ) -> None:
        """Delete a case contact."""
        # Verify case exists
        await self.get_by_id(case_id, tenant_id)

        # Get and delete contact
        stmt = select(CaseContact).where(
            CaseContact.id == contact_id,
            CaseContact.case_id == case_id,
        )
        result = await self.db.execute(stmt)
        contact = result.scalar_one_or_none()

        if not contact:
            raise NotFoundError("CaseContact", contact_id)

        await self.db.delete(contact)
        await self.db.flush()

    async def list_published_by_service(
        self,
        service_id: UUID,
        tenant_id: UUID,
        locale: str,
    ) -> list[Case]:
        """Get published cases linked to a service.
        
        Returns cases that:
        - Are linked to the specified service
        - Have status = published
        - Have the specified locale
        - Are not deleted
        """
        stmt = (
            select(Case)
            .join(CaseServiceLink, Case.id == CaseServiceLink.case_id)
            .join(CaseLocale, Case.id == CaseLocale.case_id)
            .where(CaseServiceLink.service_id == service_id)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .where(Case.status == ArticleStatus.PUBLISHED.value)
            .where(CaseLocale.locale == locale)
            .options(
                selectinload(Case.locales),
                selectinload(Case.services).selectinload(CaseServiceLink.service),
            )
            .order_by(Case.sort_order, Case.published_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())
