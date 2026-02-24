"""Unit tests for company ServiceService."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError, DuplicatePriceError, DuplicateTagError
from app.modules.company.models import Service, ServiceLocale, ServicePrice, ServiceTag
from app.modules.company.services import ServiceService


class TestServiceService:
    """Tests for ServiceService - read and write operations."""

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
    def service_service(self, mock_db: AsyncMock) -> ServiceService:
        """Create ServiceService with mocked dependencies."""
        return ServiceService(mock_db)

    @pytest.fixture
    def sample_service(self) -> Service:
        """Create sample service for testing."""
        service = Service(
            id=uuid4(),
            tenant_id=uuid4(),
            icon="icon-web",
            image_url="https://example.com/image.jpg",
            price_from=100000,
            price_currency="RUB",
            is_published=False,
            sort_order=0,
            version=1,
        )
        service.locales = [
            ServiceLocale(
                id=uuid4(),
                service_id=service.id,
                locale="ru",
                slug="web-development",
                title="Веб-разработка",
                short_description="Создание сайтов",
                description="<p>Полное описание</p>",
            )
        ]
        service.prices = []
        service.tags = []
        return service

    @pytest.fixture
    def published_service(self, sample_service: Service) -> Service:
        """Create published service."""
        sample_service.is_published = True
        sample_service.published_at = datetime.now(UTC)
        return sample_service

    # ========== get_by_id Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        sample_service: Service,
    ) -> None:
        """Get by ID should return service when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_service
        mock_db.execute.return_value = mock_result

        service = await service_service.get_by_id(sample_service.id, sample_service.tenant_id)

        assert service.id == sample_service.id
        assert service.icon == "icon-web"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when service doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await service_service.get_by_id(uuid4(), uuid4())

    # ========== get_by_slug Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_success(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        published_service: Service,
    ) -> None:
        """Get by slug should return published service."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = published_service
        mock_db.execute.return_value = mock_result

        service = await service_service.get_by_slug(
            "web-development", "ru", published_service.tenant_id
        )

        assert service.is_published is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by slug should raise NotFoundError when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await service_service.get_by_slug("nonexistent", "ru", uuid4())

    # ========== list_services Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_services_empty(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
    ) -> None:
        """List services should return empty list when no services."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        services, total = await service_service.list_services(uuid4())

        assert services == []
        assert total == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_services_with_published_filter(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        published_service: Service,
    ) -> None:
        """List services should filter by is_published."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [published_service]

        mock_db.execute.side_effect = [count_result, list_result]

        services, total = await service_service.list_services(
            published_service.tenant_id,
            is_published=True,
        )

        assert len(services) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_services_with_pagination(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        sample_service: Service,
    ) -> None:
        """List services should support pagination."""
        count_result = Mock()
        count_result.scalar.return_value = 25

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_service] * 10

        mock_db.execute.side_effect = [count_result, list_result]

        services, total = await service_service.list_services(
            sample_service.tenant_id,
            page=2,
            page_size=10,
        )

        assert len(services) == 10
        assert total == 25

    # ========== list_published Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_services(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        published_service: Service,
    ) -> None:
        """List published should only return published services for locale."""
        mock_result = Mock()
        # Use unique() for this query
        mock_result.scalars.return_value.unique.return_value.all.return_value = [published_service]
        mock_db.execute.return_value = mock_result

        services = await service_service.list_published(
            published_service.tenant_id, locale="ru"
        )

        assert len(services) == 1
        assert services[0].is_published is True

    # ========== soft_delete Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        sample_service: Service,
    ) -> None:
        """Soft delete should mark service as deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_service
        mock_db.execute.return_value = mock_result

        assert sample_service.deleted_at is None

        await service_service.soft_delete(sample_service.id, sample_service.tenant_id)

        assert sample_service.deleted_at is not None
        mock_db.flush.assert_called()

    # ========== Price Management Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_price_success(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        sample_service: Service,
    ) -> None:
        """Create price should add new price for locale/currency."""
        from app.modules.company.schemas import ServicePriceCreate
        
        # First call: get_by_id
        get_result = Mock()
        get_result.scalar_one_or_none.return_value = sample_service
        
        # Second call: check existing price
        check_result = Mock()
        check_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [get_result, check_result]

        price_data = ServicePriceCreate(locale="ru", price=150000, currency="RUB")
        
        # The actual service method adds and flushes
        price = await service_service.create_price(
            sample_service.id, sample_service.tenant_id, price_data
        )

        mock_db.add.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_price_duplicate(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        sample_service: Service,
    ) -> None:
        """Create price should raise error if locale/currency combo exists."""
        from app.modules.company.schemas import ServicePriceCreate
        
        existing_price = ServicePrice(
            id=uuid4(),
            service_id=sample_service.id,
            locale="ru",
            price=100000,
            currency="RUB",
        )
        
        # First call: get_by_id
        get_result = Mock()
        get_result.scalar_one_or_none.return_value = sample_service
        
        # Second call: check existing price - returns existing
        check_result = Mock()
        check_result.scalar_one_or_none.return_value = existing_price
        
        mock_db.execute.side_effect = [get_result, check_result]

        price_data = ServicePriceCreate(locale="ru", price=150000, currency="RUB")
        
        with pytest.raises(DuplicatePriceError):
            await service_service.create_price(
                sample_service.id, sample_service.tenant_id, price_data
            )

    # ========== Tag Management Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_tag_success(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        sample_service: Service,
    ) -> None:
        """Create tag should add new tag for locale."""
        from app.modules.company.schemas import ServiceTagCreate
        
        # First call: get_by_id
        get_result = Mock()
        get_result.scalar_one_or_none.return_value = sample_service
        
        # Second call: check existing tag
        check_result = Mock()
        check_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [get_result, check_result]

        tag_data = ServiceTagCreate(locale="ru", tag="новый тег")
        
        await service_service.create_tag(
            sample_service.id, sample_service.tenant_id, tag_data
        )

        mock_db.add.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_tag_duplicate(
        self,
        service_service: ServiceService,
        mock_db: AsyncMock,
        sample_service: Service,
    ) -> None:
        """Create tag should raise error if tag already exists for locale."""
        from app.modules.company.schemas import ServiceTagCreate
        
        existing_tag = ServiceTag(
            id=uuid4(),
            service_id=sample_service.id,
            locale="ru",
            tag="existing",
        )
        
        # First call: get_by_id
        get_result = Mock()
        get_result.scalar_one_or_none.return_value = sample_service
        
        # Second call: check existing tag - returns existing
        check_result = Mock()
        check_result.scalar_one_or_none.return_value = existing_tag
        
        mock_db.execute.side_effect = [get_result, check_result]

        tag_data = ServiceTagCreate(locale="ru", tag="existing")
        
        with pytest.raises(DuplicateTagError):
            await service_service.create_tag(
                sample_service.id, sample_service.tenant_id, tag_data
            )
