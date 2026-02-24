"""Unit tests for company EmployeeService."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.company.models import (
    Employee,
    EmployeeLocale,
    EmployeePracticeArea,
    PracticeArea,
)
from app.modules.company.services import EmployeeService


class TestEmployeeService:
    """Tests for EmployeeService - read and write operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        db = AsyncMock()
        db.add = Mock()
        db.delete = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def employee_service(self, mock_db: AsyncMock) -> EmployeeService:
        """Create EmployeeService with mocked dependencies."""
        return EmployeeService(mock_db)

    @pytest.fixture
    def sample_employee(self) -> Employee:
        """Create sample employee for testing."""
        employee = Employee(
            id=uuid4(),
            tenant_id=uuid4(),
            photo_url="https://example.com/photo.jpg",
            email="john@example.com",
            phone="+7 999 123-45-67",
            linkedin_url="https://linkedin.com/in/johndoe",
            is_published=False,
            sort_order=0,
            version=1,
        )
        employee.locales = [
            EmployeeLocale(
                id=uuid4(),
                employee_id=employee.id,
                locale="ru",
                slug="john-doe",
                first_name="Иван",
                last_name="Иванов",
                position="Разработчик",
                bio="<p>Опытный специалист</p>",
            )
        ]
        employee.practice_areas = []
        return employee

    @pytest.fixture
    def published_employee(self, sample_employee: Employee) -> Employee:
        """Create published employee."""
        sample_employee.is_published = True
        sample_employee.published_at = datetime.now(UTC)
        return sample_employee

    @pytest.fixture
    def sample_practice_area(self) -> PracticeArea:
        """Create sample practice area."""
        return PracticeArea(
            id=uuid4(),
            tenant_id=uuid4(),
            icon="icon-web",
            is_published=True,
            sort_order=0,
            version=1,
        )

    # ========== get_by_id Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        sample_employee: Employee,
    ) -> None:
        """Get by ID should return employee when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_employee
        mock_db.execute.return_value = mock_result

        employee = await employee_service.get_by_id(
            sample_employee.id, sample_employee.tenant_id
        )

        assert employee.id == sample_employee.id
        assert employee.email == "john@example.com"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when employee doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await employee_service.get_by_id(uuid4(), uuid4())

    # ========== get_by_slug Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_success(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        published_employee: Employee,
    ) -> None:
        """Get by slug should return published employee."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = published_employee
        mock_db.execute.return_value = mock_result

        employee = await employee_service.get_by_slug(
            "john-doe", "ru", published_employee.tenant_id
        )

        assert employee.is_published is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by slug should raise NotFoundError when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await employee_service.get_by_slug("nonexistent", "ru", uuid4())

    # ========== list_employees Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_employees_empty(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
    ) -> None:
        """List employees should return empty list when no employees."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        employees, total = await employee_service.list_employees(uuid4())

        assert employees == []
        assert total == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_employees_with_published_filter(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        published_employee: Employee,
    ) -> None:
        """List employees should filter by is_published."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [
            published_employee
        ]

        mock_db.execute.side_effect = [count_result, list_result]

        employees, total = await employee_service.list_employees(
            published_employee.tenant_id,
            is_published=True,
        )

        assert len(employees) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_employees_with_search(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        sample_employee: Employee,
    ) -> None:
        """List employees should support search by name/position/email."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [
            sample_employee
        ]

        mock_db.execute.side_effect = [count_result, list_result]

        employees, total = await employee_service.list_employees(
            sample_employee.tenant_id,
            search="Иван",
        )

        assert len(employees) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_employees_with_pagination(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        sample_employee: Employee,
    ) -> None:
        """List employees should support pagination."""
        count_result = Mock()
        count_result.scalar.return_value = 25

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = (
            [sample_employee] * 10
        )

        mock_db.execute.side_effect = [count_result, list_result]

        employees, total = await employee_service.list_employees(
            sample_employee.tenant_id,
            page=2,
            page_size=10,
        )

        assert len(employees) == 10
        assert total == 25

    # ========== list_published Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_employees(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        published_employee: Employee,
    ) -> None:
        """List published should only return published employees for locale."""
        mock_result = Mock()
        mock_result.scalars.return_value.unique.return_value.all.return_value = [
            published_employee
        ]
        mock_db.execute.return_value = mock_result

        employees = await employee_service.list_published(
            published_employee.tenant_id, locale="ru"
        )

        assert len(employees) == 1
        assert employees[0].is_published is True

    # ========== soft_delete Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        sample_employee: Employee,
    ) -> None:
        """Soft delete should mark employee as deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_employee
        mock_db.execute.return_value = mock_result

        assert sample_employee.deleted_at is None

        await employee_service.soft_delete(
            sample_employee.id, sample_employee.tenant_id
        )

        assert sample_employee.deleted_at is not None
        mock_db.flush.assert_called()

    # ========== Practice Areas Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_employee_with_practice_areas(
        self,
        employee_service: EmployeeService,
        mock_db: AsyncMock,
        sample_employee: Employee,
        sample_practice_area: PracticeArea,
    ) -> None:
        """Employee should be able to have practice areas."""
        # Create link
        link = EmployeePracticeArea(
            id=uuid4(),
            employee_id=sample_employee.id,
            practice_area_id=sample_practice_area.id,
        )
        link.practice_area = sample_practice_area
        sample_employee.practice_areas = [link]

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_employee
        mock_db.execute.return_value = mock_result

        employee = await employee_service.get_by_id(
            sample_employee.id, sample_employee.tenant_id
        )

        assert len(employee.practice_areas) == 1
        assert employee.practice_areas[0].practice_area_id == sample_practice_area.id
