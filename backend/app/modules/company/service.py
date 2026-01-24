"""Company module service layer."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import (
    DuplicatePriceError,
    DuplicateTagError,
    NotFoundError,
)
from app.core.locale_helpers import (
    LocaleAlreadyExistsError,
    MinimumLocalesError,
    check_locale_exists,
    check_slug_unique,
    count_locales,
    get_locale_by_id,
    update_locale_fields,
)
from app.modules.company.models import (
    Address,
    AddressLocale,
    Advantage,
    AdvantageLocale,
    Contact,
    Employee,
    EmployeeLocale,
    EmployeePracticeArea,
    PracticeArea,
    PracticeAreaLocale,
    Service,
    ServiceLocale,
    ServicePrice,
    ServiceTag,
)
from app.modules.company.schemas import (
    AddressCreate,
    AddressLocaleCreate,
    AddressLocaleUpdate,
    AddressUpdate,
    AdvantageCreate,
    AdvantageLocaleCreate,
    AdvantageLocaleUpdate,
    AdvantageUpdate,
    ContactCreate,
    ContactUpdate,
    EmployeeCreate,
    EmployeeLocaleCreate,
    EmployeeLocaleUpdate,
    EmployeeUpdate,
    PracticeAreaCreate,
    PracticeAreaLocaleCreate,
    PracticeAreaLocaleUpdate,
    PracticeAreaUpdate,
    ServiceCreate,
    ServiceLocaleCreate,
    ServiceLocaleUpdate,
    ServicePriceCreate,
    ServicePriceUpdate,
    ServiceTagCreate,
    ServiceUpdate,
)


class ServiceService:
    """Service for managing services."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, service_id: UUID, tenant_id: UUID) -> Service:
        """Get service by ID."""
        stmt = (
            select(Service)
            .where(Service.id == service_id)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
            .options(
                selectinload(Service.locales),
                selectinload(Service.prices),
                selectinload(Service.tags),
            )
        )
        result = await self.db.execute(stmt)
        service = result.scalar_one_or_none()

        if not service:
            raise NotFoundError("Service", service_id)

        return service

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
        base_query = (
            select(Service)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
        )

        if is_published is not None:
            base_query = base_query.where(Service.is_published == is_published)

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(
                selectinload(Service.locales),
                selectinload(Service.prices),
                selectinload(Service.tags),
            )
            .order_by(Service.sort_order, Service.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        services = list(result.scalars().all())

        return services, total

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
            service.published_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(service, field, value)

        await self.db.flush()
        await self.db.refresh(service)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(service, ["locales", "prices", "tags"])

        return service

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
        service = await self.get_by_id(service_id, tenant_id)
        service.soft_delete()
        await self.db.flush()

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


class EmployeeService:
    """Service for managing employees."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, employee_id: UUID, tenant_id: UUID) -> Employee:
        """Get employee by ID."""
        stmt = (
            select(Employee)
            .where(Employee.id == employee_id)
            .where(Employee.tenant_id == tenant_id)
            .where(Employee.deleted_at.is_(None))
            .options(
                selectinload(Employee.locales),
                selectinload(Employee.practice_areas).selectinload(
                    EmployeePracticeArea.practice_area
                ),
            )
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()

        if not employee:
            raise NotFoundError("Employee", employee_id)

        return employee

    async def get_by_slug(self, slug: str, locale: str, tenant_id: UUID) -> Employee:
        """Get published employee by slug."""
        stmt = (
            select(Employee)
            .join(EmployeeLocale)
            .where(Employee.tenant_id == tenant_id)
            .where(Employee.deleted_at.is_(None))
            .where(Employee.is_published.is_(True))
            .where(EmployeeLocale.locale == locale)
            .where(EmployeeLocale.slug == slug)
            .options(selectinload(Employee.locales))
        )
        result = await self.db.execute(stmt)
        employee = result.scalar_one_or_none()

        if not employee:
            raise NotFoundError("Employee", slug)

        return employee

    async def list_employees(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_published: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Employee], int]:
        """List employees with pagination."""
        base_query = (
            select(Employee)
            .where(Employee.tenant_id == tenant_id)
            .where(Employee.deleted_at.is_(None))
        )

        if is_published is not None:
            base_query = base_query.where(Employee.is_published == is_published)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(EmployeeLocale).where(
                (EmployeeLocale.name.ilike(search_pattern)) |
                (EmployeeLocale.position.ilike(search_pattern)) |
                (Employee.email.ilike(search_pattern))
            ).distinct()

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(selectinload(Employee.locales))
            .order_by(Employee.sort_order, Employee.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        employees = list(result.scalars().unique().all())

        return employees, total

    async def list_published(self, tenant_id: UUID, locale: str) -> list[Employee]:
        """List published employees for public API."""
        # Filter by locale at database level to ensure only employees with the locale are returned
        stmt = (
            select(Employee)
            .join(EmployeeLocale, Employee.id == EmployeeLocale.employee_id)
            .where(Employee.tenant_id == tenant_id)
            .where(Employee.deleted_at.is_(None))
            .where(Employee.is_published.is_(True))
            .where(EmployeeLocale.locale == locale)
            .options(selectinload(Employee.locales))
            .order_by(Employee.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    @transactional
    async def create(self, tenant_id: UUID, data: EmployeeCreate) -> Employee:
        """Create a new employee."""
        # Create employee (photo_url is set via separate endpoint)
        employee = Employee(
            tenant_id=tenant_id,
            email=data.email,
            phone=data.phone,
            linkedin_url=data.linkedin_url,
            telegram_url=data.telegram_url,
            is_published=data.is_published,
            sort_order=data.sort_order,
        )
        self.db.add(employee)
        await self.db.flush()

        # Create locales
        for locale_data in data.locales:
            locale = EmployeeLocale(
                employee_id=employee.id,
                **locale_data.model_dump(),
            )
            self.db.add(locale)

        # Add practice areas
        for pa_id in data.practice_area_ids:
            epa = EmployeePracticeArea(employee_id=employee.id, practice_area_id=pa_id)
            self.db.add(epa)

        await self.db.flush()
        await self.db.refresh(employee)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(employee, ["locales", "practice_areas"])

        return employee

    @transactional
    async def update(self, employee_id: UUID, tenant_id: UUID, data: EmployeeUpdate) -> Employee:
        """Update employee."""
        employee = await self.get_by_id(employee_id, tenant_id)
        employee.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version", "practice_area_ids"})

        # Handle publishing
        if "is_published" in update_data and update_data["is_published"] and not employee.is_published:
            employee.published_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(employee, field, value)

        # Update practice areas if provided
        if data.practice_area_ids is not None:
            # Remove existing
            for epa in employee.practice_areas:
                await self.db.delete(epa)

            # Add new
            for pa_id in data.practice_area_ids:
                epa = EmployeePracticeArea(employee_id=employee.id, practice_area_id=pa_id)
                self.db.add(epa)

        await self.db.flush()
        await self.db.refresh(employee)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(employee, ["locales", "practice_areas"])

        return employee

    @transactional
    async def soft_delete(self, employee_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an employee."""
        employee = await self.get_by_id(employee_id, tenant_id)
        employee.soft_delete()
        await self.db.flush()

    # ========== Locale Management ==========

    @transactional
    async def create_locale(
        self, employee_id: UUID, tenant_id: UUID, data: EmployeeLocaleCreate
    ) -> EmployeeLocale:
        """Create a new locale for an employee."""
        # Verify employee exists
        await self.get_by_id(employee_id, tenant_id)

        # Check if locale already exists
        if await check_locale_exists(
            self.db, EmployeeLocale, "employee_id", employee_id, data.locale
        ):
            raise LocaleAlreadyExistsError("Employee", data.locale)

        # Check slug uniqueness
        await check_slug_unique(
            self.db, EmployeeLocale, Employee, "employee_id",
            data.slug, data.locale, tenant_id
        )

        locale = EmployeeLocale(
            employee_id=employee_id,
            **data.model_dump(),
        )
        self.db.add(locale)
        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def update_locale(
        self, locale_id: UUID, employee_id: UUID, tenant_id: UUID, data: EmployeeLocaleUpdate
    ) -> EmployeeLocale:
        """Update an employee locale."""
        # Verify employee exists
        await self.get_by_id(employee_id, tenant_id)

        # Get locale
        locale = await get_locale_by_id(
            self.db, EmployeeLocale, locale_id, "employee_id", employee_id, "Employee"
        )

        # Check slug uniqueness if slug is being updated
        if data.slug and data.slug != locale.slug:
            await check_slug_unique(
                self.db, EmployeeLocale, Employee, "employee_id",
                data.slug, locale.locale, tenant_id, exclude_locale_id=locale_id
            )

        # Update fields
        update_locale_fields(
            locale, data,
            ["first_name", "last_name", "slug", "position", "bio", "meta_title", "meta_description"]
        )

        await self.db.flush()
        await self.db.refresh(locale)

        return locale

    @transactional
    async def delete_locale(self, locale_id: UUID, employee_id: UUID, tenant_id: UUID) -> None:
        """Delete an employee locale."""
        # Verify employee exists
        await self.get_by_id(employee_id, tenant_id)

        # Check minimum locales
        locale_count = await count_locales(self.db, EmployeeLocale, "employee_id", employee_id)
        if locale_count <= 1:
            raise MinimumLocalesError("Employee")

        # Get and delete locale
        locale = await get_locale_by_id(
            self.db, EmployeeLocale, locale_id, "employee_id", employee_id, "Employee"
        )
        await self.db.delete(locale)
        await self.db.flush()


class PracticeAreaService:
    """Service for managing practice areas."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, pa_id: UUID, tenant_id: UUID) -> PracticeArea:
        """Get practice area by ID."""
        stmt = (
            select(PracticeArea)
            .where(PracticeArea.id == pa_id)
            .where(PracticeArea.tenant_id == tenant_id)
            .where(PracticeArea.deleted_at.is_(None))
            .options(selectinload(PracticeArea.locales))
        )
        result = await self.db.execute(stmt)
        pa = result.scalar_one_or_none()

        if not pa:
            raise NotFoundError("PracticeArea", pa_id)

        return pa

    async def list_all(self, tenant_id: UUID) -> list[PracticeArea]:
        """List all practice areas for admin."""
        stmt = (
            select(PracticeArea)
            .where(PracticeArea.tenant_id == tenant_id)
            .where(PracticeArea.deleted_at.is_(None))
            .options(selectinload(PracticeArea.locales))
            .order_by(PracticeArea.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
        pa = await self.get_by_id(pa_id, tenant_id)
        pa.soft_delete()
        await self.db.flush()

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


class AdvantageService:
    """Service for managing advantages."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, adv_id: UUID, tenant_id: UUID) -> Advantage:
        """Get advantage by ID."""
        stmt = (
            select(Advantage)
            .where(Advantage.id == adv_id)
            .where(Advantage.tenant_id == tenant_id)
            .where(Advantage.deleted_at.is_(None))
            .options(selectinload(Advantage.locales))
        )
        result = await self.db.execute(stmt)
        adv = result.scalar_one_or_none()

        if not adv:
            raise NotFoundError("Advantage", adv_id)

        return adv

    async def list_all(self, tenant_id: UUID) -> list[Advantage]:
        """List all advantages for admin."""
        stmt = (
            select(Advantage)
            .where(Advantage.tenant_id == tenant_id)
            .where(Advantage.deleted_at.is_(None))
            .options(selectinload(Advantage.locales))
            .order_by(Advantage.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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
        adv = await self.get_by_id(adv_id, tenant_id)
        adv.soft_delete()
        await self.db.flush()

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

