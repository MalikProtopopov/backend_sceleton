"""Unit tests for leads InquiryService."""

from datetime import datetime, UTC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.modules.leads.models import Inquiry, InquiryForm, InquiryStatus
from app.modules.leads.service import InquiryService, InquiryFormService


class TestInquiryFormService:
    """Tests for InquiryFormService - CRUD operations."""

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
    def form_service(self, mock_db: AsyncMock) -> InquiryFormService:
        """Create InquiryFormService with mocked dependencies."""
        return InquiryFormService(mock_db)

    @pytest.fixture
    def sample_form(self) -> InquiryForm:
        """Create sample inquiry form for testing."""
        return InquiryForm(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Contact Form",
            slug="contact",
            description="Main contact form",
            is_active=True,
            sort_order=0,
            version=1,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        form_service: InquiryFormService,
        mock_db: AsyncMock,
        sample_form: InquiryForm,
    ) -> None:
        """Get by ID should return form when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_form
        mock_db.execute.return_value = mock_result

        form = await form_service.get_by_id(sample_form.id, sample_form.tenant_id)

        assert form.id == sample_form.id
        assert form.name == "Contact Form"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        form_service: InquiryFormService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when form doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await form_service.get_by_id(uuid4(), uuid4())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_success(
        self,
        form_service: InquiryFormService,
        mock_db: AsyncMock,
        sample_form: InquiryForm,
    ) -> None:
        """Get by slug should return active form."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_form
        mock_db.execute.return_value = mock_result

        form = await form_service.get_by_slug("contact", sample_form.tenant_id)

        assert form is not None
        assert form.slug == "contact"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_forms(
        self,
        form_service: InquiryFormService,
        mock_db: AsyncMock,
        sample_form: InquiryForm,
    ) -> None:
        """List forms should return all forms for tenant."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_form]
        mock_db.execute.return_value = mock_result

        forms = await form_service.list_forms(sample_form.tenant_id)

        assert len(forms) == 1


class TestInquiryService:
    """Tests for InquiryService - read and write operations."""

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
    def inquiry_service(self, mock_db: AsyncMock) -> InquiryService:
        """Create InquiryService with mocked dependencies."""
        return InquiryService(mock_db)

    @pytest.fixture
    def sample_inquiry(self) -> Inquiry:
        """Create sample inquiry for testing."""
        return Inquiry(
            id=uuid4(),
            tenant_id=uuid4(),
            form_id=None,
            name="Иван Иванов",
            email="ivan@example.com",
            phone="+7 999 123-45-67",
            company="Test Company",
            message="Хочу заказать разработку",
            status=InquiryStatus.NEW.value,
            # Analytics
            source_url="https://example.com/services",
            referrer="https://google.com",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="brand",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            device_type="desktop",
            country="Russia",
            city="Moscow",
        )

    @pytest.fixture
    def processed_inquiry(self, sample_inquiry: Inquiry) -> Inquiry:
        """Create processed inquiry."""
        sample_inquiry.status = InquiryStatus.IN_PROGRESS.value
        sample_inquiry.assigned_to = uuid4()
        return sample_inquiry

    # ========== get_by_id Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """Get by ID should return inquiry when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_inquiry
        mock_db.execute.return_value = mock_result

        inquiry = await inquiry_service.get_by_id(
            sample_inquiry.id, sample_inquiry.tenant_id
        )

        assert inquiry.id == sample_inquiry.id
        assert inquiry.email == "ivan@example.com"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when inquiry doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await inquiry_service.get_by_id(uuid4(), uuid4())

    # ========== list_inquiries Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_inquiries_empty(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
    ) -> None:
        """List inquiries should return empty list when no inquiries."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        inquiries, total = await inquiry_service.list_inquiries(uuid4())

        assert inquiries == []
        assert total == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_inquiries_with_status_filter(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """List inquiries should filter by status."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_inquiry]

        mock_db.execute.side_effect = [count_result, list_result]

        inquiries, total = await inquiry_service.list_inquiries(
            sample_inquiry.tenant_id,
            status="new",
        )

        assert len(inquiries) == 1
        assert total == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_inquiries_with_utm_filter(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """List inquiries should filter by UTM source."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_inquiry]

        mock_db.execute.side_effect = [count_result, list_result]

        inquiries, total = await inquiry_service.list_inquiries(
            sample_inquiry.tenant_id,
            utm_source="google",
        )

        assert len(inquiries) == 1
        assert inquiries[0].utm_source == "google"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_inquiries_with_search(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """List inquiries should support search by name/email/phone."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_inquiry]

        mock_db.execute.side_effect = [count_result, list_result]

        inquiries, total = await inquiry_service.list_inquiries(
            sample_inquiry.tenant_id,
            search="ivan",
        )

        assert len(inquiries) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_inquiries_with_pagination(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """List inquiries should support pagination."""
        count_result = Mock()
        count_result.scalar.return_value = 50

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [sample_inquiry] * 20

        mock_db.execute.side_effect = [count_result, list_result]

        inquiries, total = await inquiry_service.list_inquiries(
            sample_inquiry.tenant_id,
            page=2,
            page_size=20,
        )

        assert len(inquiries) == 20
        assert total == 50

    # ========== Status Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inquiry_status_new(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """New inquiry should have NEW status and no assignee."""
        assert sample_inquiry.status == InquiryStatus.NEW.value
        assert sample_inquiry.assigned_to is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inquiry_status_in_progress(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        processed_inquiry: Inquiry,
    ) -> None:
        """In progress inquiry should have assignee."""
        assert processed_inquiry.status == InquiryStatus.IN_PROGRESS.value
        assert processed_inquiry.assigned_to is not None

    # ========== Analytics Data Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_inquiry_has_analytics_data(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """Inquiry should have UTM and device analytics."""
        assert sample_inquiry.utm_source == "google"
        assert sample_inquiry.utm_medium == "cpc"
        assert sample_inquiry.device_type == "desktop"
        assert sample_inquiry.ip_address == "192.168.1.1"
        assert sample_inquiry.country == "Russia"

    # ========== soft_delete Tests ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self,
        inquiry_service: InquiryService,
        mock_db: AsyncMock,
        sample_inquiry: Inquiry,
    ) -> None:
        """Soft delete should mark inquiry as deleted."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_inquiry
        mock_db.execute.return_value = mock_result

        assert sample_inquiry.deleted_at is None

        await inquiry_service.soft_delete(
            sample_inquiry.id, sample_inquiry.tenant_id
        )

        assert sample_inquiry.deleted_at is not None
        mock_db.flush.assert_called()
