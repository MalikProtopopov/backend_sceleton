"""Company module - service service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import (
    DuplicatePriceError,
    DuplicateTagError,
    NotFoundError,
)
from app.core.pagination import paginate_query
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
    Service,
    ServiceLocale,
    ServicePrice,
    ServiceTag,
)
from app.modules.company.schemas import (
    ServiceCreate,
    ServiceLocaleCreate,
    ServiceLocaleUpdate,
    ServicePriceCreate,
    ServicePriceUpdate,
    ServiceTagCreate,
    ServiceUpdate,
)


class ServiceService(BaseService[Service]):
    """Service for managing services."""

    model = Service

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [
            selectinload(Service.locales),
            selectinload(Service.prices),
            selectinload(Service.tags),
        ]

    async def get_by_id(self, service_id: UUID, tenant_id: UUID) -> Service:
        """Get service by ID."""
        return await self._get_by_id(service_id, tenant_id)

    async def get_by_slug(self, slug: str, locale: str, tenant_id: UUID) -> Service:
        """Get published service by slug and locale."""
        stmt = (
            select(Service)
            .join(ServiceLocale)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
            .where(Service.is_published.is_(True))
            .where(ServiceLocale.locale == locale)
            .where(ServiceLocale.slug == slug)
            .options(
                selectinload(Service.locales),
                selectinload(Service.prices),
                selectinload(Service.tags),
            )
        )
        result = await self.db.execute(stmt)
        service = result.scalar_one_or_none()

        if not service:
            raise NotFoundError("Service", slug)

        return service

    async def list_services(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_published: bool | None = None,
    ) -> tuple[list[Service], int]:
        """List services with pagination."""
        filters = []
        if is_published is not None:
            filters.append(Service.is_published == is_published)

        base_query = self._build_base_query(tenant_id, filters=filters)

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=self._get_default_options(),
            order_by=[Service.sort_order, Service.created_at.desc()],
        )

    async def list_published(self, tenant_id: UUID, locale: str) -> list[Service]:
        """List published services for public API."""
        # Filter by locale at database level to ensure only services with the locale are returned
        stmt = (
            select(Service)
            .join(ServiceLocale, Service.id == ServiceLocale.service_id)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
            .where(Service.is_published.is_(True))
            .where(ServiceLocale.locale == locale)
            .options(
                selectinload(Service.locales),
                selectinload(Service.prices),
                selectinload(Service.tags),
            )
            .order_by(Service.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    @transactional
    async def create(self, tenant_id: UUID, data: ServiceCreate) -> Service:
        """Create a new service."""
        # Check slug uniqueness per locale
        for locale_data in data.locales:
            await check_slug_unique(
                self.db, ServiceLocale, Service, "service_id",
                locale_data.slug, locale_data.locale, tenant_id
            )

        # Create service (image_url is set via separate endpoint)
        service = Service(
            tenant_id=tenant_id,
            icon=data.icon,
            price_from=data.price_from,
            price_currency=data.price_currency,
            is_published=data.is_published,
            sort_order=data.sort_order,
        )
        self.db.add(service)
        await self.db.flush()

        # Create locales
        for locale_data in data.locales:
            locale = ServiceLocale(
                service_id=service.id,
                **locale_data.model_dump(),
            )
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(service)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(service, ["locales", "prices", "tags"])

        return service

    @transactional
    async def update(self, service_id: UUID, tenant_id: UUID, data: ServiceUpdate) -> Service:
        """Update service."""
        service = await self.get_by_id(service_id, tenant_id)
        service.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        # Handle publishing
        if "is_published" in update_data and update_data["is_published"] and not service.is_published:
            service.published_at = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(service, field, value)

        await self.db.flush()
        await self.db.refresh(service)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(service, ["locales", "prices", "tags"])

        return service

    @transactional
    async def update_image_url(
        self, service_id: UUID, tenant_id: UUID, url: str | None
    ) -> "Service":
        """Update or clear the service image URL."""
        svc = await self.get_by_id(service_id, tenant_id)
        svc.image_url = url
        await self.db.flush()
        await self.db.refresh(svc)
        await self.db.refresh(svc, ["locales", "prices", "tags"])
        return svc

    @transactional
    async def create_price(
        self, service_id: UUID, tenant_id: UUID, data: ServicePriceCreate
    ) -> ServicePrice:
        """Create a price for a service."""
        # Verify service exists and belongs to tenant
        service = await self.get_by_id(service_id, tenant_id)

        # Check if price already exists for this locale+currency
        stmt = (
            select(ServicePrice)
            .where(ServicePrice.service_id == service_id)
            .where(ServicePrice.locale == data.locale)
            .where(ServicePrice.currency == data.currency)
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise DuplicatePriceError(data.locale, data.currency)

        price = ServicePrice(
            service_id=service_id,
            locale=data.locale,
            price=data.price,
            currency=data.currency,
        )
        self.db.add(price)
        await self.db.flush()
        await self.db.refresh(price)

        return price

    @transactional
    async def update_price(
        self, price_id: UUID, service_id: UUID, tenant_id: UUID, data: ServicePriceUpdate
    ) -> ServicePrice:
        """Update a service price."""
        # Verify service exists and belongs to tenant
        await self.get_by_id(service_id, tenant_id)

        stmt = (
            select(ServicePrice)
            .where(ServicePrice.id == price_id)
            .where(ServicePrice.service_id == service_id)
        )
        result = await self.db.execute(stmt)
        price = result.scalar_one_or_none()

        if not price:
            raise NotFoundError("ServicePrice", price_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(price, field, value)

        await self.db.flush()
        await self.db.refresh(price)

        return price

    @transactional
    async def delete_price(self, price_id: UUID, service_id: UUID, tenant_id: UUID) -> None:
        """Delete a service price."""
        # Verify service exists and belongs to tenant
        await self.get_by_id(service_id, tenant_id)

        stmt = (
            select(ServicePrice)
            .where(ServicePrice.id == price_id)
            .where(ServicePrice.service_id == service_id)
        )
        result = await self.db.execute(stmt)
        price = result.scalar_one_or_none()

        if not price:
            raise NotFoundError("ServicePrice", price_id)

        await self.db.delete(price)
        await self.db.flush()

    @transactional
    async def create_tag(
        self, service_id: UUID, tenant_id: UUID, data: ServiceTagCreate
    ) -> ServiceTag:
        """Create a tag for a service."""
        # Verify service exists and belongs to tenant
        service = await self.get_by_id(service_id, tenant_id)

        # Check if tag already exists for this locale+tag
        stmt = (
            select(ServiceTag)
            .where(ServiceTag.service_id == service_id)
            .where(ServiceTag.locale == data.locale)
            .where(ServiceTag.tag == data.tag)
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise DuplicateTagError(data.tag, data.locale)

        tag = ServiceTag(
            service_id=service_id,
            locale=data.locale,
            tag=data.tag,
        )
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)

        return tag

    @transactional
    async def update_tag(
        self, tag_id: UUID, service_id: UUID, tenant_id: UUID, data: ServiceTagCreate
    ) -> ServiceTag:
        """Update a service tag."""
        # Verify service exists and belongs to tenant
        await self.get_by_id(service_id, tenant_id)

        stmt = (
            select(ServiceTag)
            .where(ServiceTag.id == tag_id)
            .where(ServiceTag.service_id == service_id)
        )
        result = await self.db.execute(stmt)
        tag = result.scalar_one_or_none()

        if not tag:
            raise NotFoundError("ServiceTag", tag_id)

        # Check if new tag already exists
        if tag.tag != data.tag or tag.locale != data.locale:
            check_stmt = (
                select(ServiceTag)
                .where(ServiceTag.service_id == service_id)
                .where(ServiceTag.locale == data.locale)
                .where(ServiceTag.tag == data.tag)
                .where(ServiceTag.id != tag_id)
            )
            check_result = await self.db.execute(check_stmt)
            if check_result.scalar_one_or_none():
                raise DuplicateTagError(data.tag, data.locale)

        tag.locale = data.locale
        tag.tag = data.tag

        await self.db.flush()
        await self.db.refresh(tag)

        return tag

    @transactional
    async def delete_tag(self, tag_id: UUID, service_id: UUID, tenant_id: UUID) -> None:
        """Delete a service tag."""
        # Verify service exists and belongs to tenant
        await self.get_by_id(service_id, tenant_id)

        stmt = (
            select(ServiceTag)
            .where(ServiceTag.id == tag_id)
            .where(ServiceTag.service_id == service_id)
        )
        result = await self.db.execute(stmt)
        tag = result.scalar_one_or_none()

        if not tag:
            raise NotFoundError("ServiceTag", tag_id)

        await self.db.delete(tag)
        await self.db.flush()

    @transactional
    async def soft_delete(self, service_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a service."""
        await self._soft_delete(service_id, tenant_id)

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, service_id: UUID, tenant_id: UUID, data: ServiceLocaleCreate
    ) -> ServiceLocale:
        """Create a new locale for a service."""
        # Verify service exists
        service = await self.get_by_id(service_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, ServiceLocale, "service_id", service_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Service", data.locale)

        # Check slug uniqueness
        await check_slug_unique(
            self.db, ServiceLocale, Service, "service_id",
            data.slug, data.locale, tenant_id
        )

        locale = ServiceLocale(
            service_id=service_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, service_id: UUID, tenant_id: UUID, data: ServiceLocaleUpdate
    ) -> ServiceLocale:
        """Update a service locale."""
        # Verify service exists
        await self.get_by_id(service_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, ServiceLocale, locale_id, "service_id", service_id, "Service"
        )

        # Check slug uniqueness if slug is being updated
        if data.slug and data.slug != locale.slug:
            await check_slug_unique(
                self.db, ServiceLocale, Service, "service_id",
                data.slug, locale.locale, tenant_id, exclude_locale_id=locale_id
            )

        # Update fields
        update_locale_fields(
            locale, data,
            ["title", "slug", "short_description", "description", "meta_title", "meta_description"]
        )

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, service_id: UUID, tenant_id: UUID) -> None:
        """Delete a service locale."""
        # Verify service exists
        await self.get_by_id(service_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, ServiceLocale, "service_id", service_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Service")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, ServiceLocale, locale_id, "service_id", service_id, "Service"
        )
        await self.db.delete(locale)
        await self.db.flush()
