"""Company module - employee service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService, update_many_to_many
from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.core.pagination import paginate_query
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
    Employee,
    EmployeeLocale,
    EmployeePracticeArea,
)
from app.modules.company.schemas import (
    EmployeeCreate,
    EmployeeLocaleCreate,
    EmployeeLocaleUpdate,
    EmployeeUpdate,
)


class EmployeeService(BaseService[Employee]):
    """Service for managing employees."""

    model = Employee

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [
            selectinload(Employee.locales),
            selectinload(Employee.practice_areas).selectinload(
                EmployeePracticeArea.practice_area
            ),
        ]

    async def get_by_id(self, employee_id: UUID, tenant_id: UUID) -> Employee:
        """Get employee by ID."""
        return await self._get_by_id(employee_id, tenant_id)

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
        filters = []
        if is_published is not None:
            filters.append(Employee.is_published == is_published)

        base_query = self._build_base_query(tenant_id, filters=filters)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(EmployeeLocale).where(
                (EmployeeLocale.first_name.ilike(search_pattern)) |
                (EmployeeLocale.last_name.ilike(search_pattern)) |
                (EmployeeLocale.position.ilike(search_pattern)) |
                (Employee.email.ilike(search_pattern))
            ).distinct()

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=[selectinload(Employee.locales)],
            order_by=[Employee.sort_order, Employee.created_at.desc()],
            unique=True,
        )

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
            employee.published_at = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(employee, field, value)

        # Update practice areas if provided
        if data.practice_area_ids is not None:
            await update_many_to_many(
                self.db,
                employee,
                "practice_areas",
                data.practice_area_ids,
                EmployeePracticeArea,
                "employee_id",
                "practice_area_id",
            )

        await self.db.flush()
        await self.db.refresh(employee)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(employee, ["locales", "practice_areas"])

        return employee

    @transactional
    async def update_photo_url(
        self, employee_id: UUID, tenant_id: UUID, url: str | None
    ) -> "Employee":
        """Update or clear the employee photo URL."""
        employee = await self.get_by_id(employee_id, tenant_id)
        employee.photo_url = url
        await self.db.flush()
        await self.db.refresh(employee)
        await self.db.refresh(employee, ["locales", "practice_areas"])
        return employee

    @transactional
    async def soft_delete(self, employee_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an employee."""
        await self._soft_delete(employee_id, tenant_id)

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
