"""Unit tests for FeatureFlagService — is_enabled, update_flag with audit."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tenants.models import FeatureFlag
from app.modules.tenants.service import FeatureFlagService


class TestFeatureFlagService:
    """Tests for FeatureFlagService."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock(spec=AsyncSession)
        db.add = Mock()
        return db

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> FeatureFlagService:
        svc = FeatureFlagService(mock_db, actor_id=uuid4())
        svc._audit_svc = AsyncMock()
        return svc

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_enabled_true(
        self, service: FeatureFlagService, mock_db: AsyncMock,
    ) -> None:
        """is_enabled should return True when flag is enabled."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = True
        mock_db.execute.return_value = mock_result

        result = await service.is_enabled(uuid4(), "blog_module")
        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_enabled_false(
        self, service: FeatureFlagService, mock_db: AsyncMock,
    ) -> None:
        """is_enabled should return False when flag is disabled."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = False
        mock_db.execute.return_value = mock_result

        result = await service.is_enabled(uuid4(), "blog_module")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_is_enabled_not_found(
        self, service: FeatureFlagService, mock_db: AsyncMock,
    ) -> None:
        """is_enabled should return False when flag doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.is_enabled(uuid4(), "nonexistent_module")
        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_flag_creates_audit_log(
        self, service: FeatureFlagService, mock_db: AsyncMock,
    ) -> None:
        """Toggling a feature flag should create an audit log."""
        from app.modules.tenants.schemas import FeatureFlagUpdate

        flag = FeatureFlag(
            id=uuid4(),
            tenant_id=uuid4(),
            feature_name="blog_module",
            enabled=False,
        )
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = flag
        mock_db.execute.return_value = mock_result

        data = FeatureFlagUpdate(enabled=True)

        await service.update_flag(flag.tenant_id, "blog_module", data)

        service._audit_svc.log.assert_called_once()
        call_kwargs = service._audit_svc.log.call_args.kwargs
        assert call_kwargs["resource_type"] == "feature_flag"
        assert call_kwargs["action"] == "update"
        assert call_kwargs["changes"]["enabled"]["old"] == "False"
        assert call_kwargs["changes"]["enabled"]["new"] == "True"
