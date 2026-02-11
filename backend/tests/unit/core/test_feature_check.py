"""Unit tests for feature flag checking middleware (admin + public variants)."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import FeatureDisabledError, FeatureNotAvailableError


class TestFeatureDisabledError:
    """Tests for admin FeatureDisabledError response format."""

    @pytest.mark.unit
    def test_status_code_is_403(self) -> None:
        err = FeatureDisabledError("blog_module")
        assert err.status_code == 403

    @pytest.mark.unit
    def test_error_code_is_feature_disabled(self) -> None:
        err = FeatureDisabledError("blog_module")
        assert err.detail["type"].endswith("/feature_disabled")

    @pytest.mark.unit
    def test_restriction_level_is_organization(self) -> None:
        """Admin feature-disabled error should indicate organization-level restriction."""
        err = FeatureDisabledError("cases_module")
        assert err.detail["restriction_level"] == "organization"

    @pytest.mark.unit
    def test_includes_feature_name(self) -> None:
        err = FeatureDisabledError("faq_module")
        assert err.detail["feature"] == "faq_module"

    @pytest.mark.unit
    def test_includes_contact_admin_flag(self) -> None:
        err = FeatureDisabledError("blog_module")
        assert err.detail["contact_admin"] is True


class TestFeatureNotAvailableError:
    """Tests for public FeatureNotAvailableError response format."""

    @pytest.mark.unit
    def test_status_code_is_404(self) -> None:
        """Public feature error should return 404, not 403."""
        err = FeatureNotAvailableError("blog_module")
        assert err.status_code == 404

    @pytest.mark.unit
    def test_error_code_is_feature_not_available(self) -> None:
        err = FeatureNotAvailableError("blog_module")
        assert err.detail["type"].endswith("/feature_not_available")

    @pytest.mark.unit
    def test_generic_message_for_public(self) -> None:
        """Public error message should be generic (no admin contact info)."""
        err = FeatureNotAvailableError("cases_module")
        assert err.detail["detail"] == "The requested resource is not available."

    @pytest.mark.unit
    def test_includes_hint_for_developers(self) -> None:
        """Response body should contain _hint field for developers."""
        err = FeatureNotAvailableError("reviews_module")
        assert "_hint" in err.detail
        assert "disabled" in err.detail["_hint"].lower()

    @pytest.mark.unit
    def test_includes_feature_name(self) -> None:
        err = FeatureNotAvailableError("team_module")
        assert err.detail["feature"] == "team_module"


class TestPermissionDeniedErrorFormat:
    """Tests for PermissionDeniedError with restriction_level."""

    @pytest.mark.unit
    def test_restriction_level_is_user(self) -> None:
        from app.core.exceptions import PermissionDeniedError

        err = PermissionDeniedError(required_permission="articles:create")
        assert err.detail["restriction_level"] == "user"
        assert err.detail["required_permission"] == "articles:create"

    @pytest.mark.unit
    def test_status_code_is_403(self) -> None:
        from app.core.exceptions import PermissionDeniedError

        err = PermissionDeniedError()
        assert err.status_code == 403


class TestInsufficientRoleErrorFormat:
    """Tests for InsufficientRoleError with restriction_level."""

    @pytest.mark.unit
    def test_restriction_level_is_user(self) -> None:
        from app.core.exceptions import InsufficientRoleError

        err = InsufficientRoleError(required_role="admin")
        assert err.detail["restriction_level"] == "user"
        assert err.detail["required_role"] == "admin"

    @pytest.mark.unit
    def test_status_code_is_403(self) -> None:
        from app.core.exceptions import InsufficientRoleError

        err = InsufficientRoleError()
        assert err.status_code == 403


class TestRequireFeaturePublicDependency:
    """Tests for the require_feature_public() dependency function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enabled_feature_passes(self) -> None:
        """When feature is enabled, dependency should return True."""
        from app.middleware.feature_check import require_feature_public

        dep = require_feature_public("blog_module")
        # dep is Depends(...), extract the actual function
        dependency_fn = dep.dependency

        tenant_id = uuid4()

        with patch(
            "app.middleware.feature_check.FeatureFlagService"
        ) as MockService:
            mock_svc = AsyncMock()
            mock_svc.is_enabled.return_value = True
            MockService.return_value = mock_svc

            mock_db = AsyncMock()
            result = await dependency_fn(tenant_id=tenant_id, db=mock_db)

        assert result is True
        mock_svc.is_enabled.assert_called_once_with(tenant_id, "blog_module")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disabled_feature_raises_404(self) -> None:
        """When feature is disabled, dependency should raise FeatureNotAvailableError (404)."""
        from app.middleware.feature_check import require_feature_public

        dep = require_feature_public("cases_module")
        dependency_fn = dep.dependency

        tenant_id = uuid4()

        with patch(
            "app.middleware.feature_check.FeatureFlagService"
        ) as MockService:
            mock_svc = AsyncMock()
            mock_svc.is_enabled.return_value = False
            MockService.return_value = mock_svc

            mock_db = AsyncMock()
            with pytest.raises(FeatureNotAvailableError) as exc_info:
                await dependency_fn(tenant_id=tenant_id, db=mock_db)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["feature"] == "cases_module"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_nonexistent_feature_raises_404(self) -> None:
        """When feature flag doesn't exist, is_enabled returns False -> 404."""
        from app.middleware.feature_check import require_feature_public

        dep = require_feature_public("nonexistent_module")
        dependency_fn = dep.dependency

        tenant_id = uuid4()

        with patch(
            "app.middleware.feature_check.FeatureFlagService"
        ) as MockService:
            mock_svc = AsyncMock()
            mock_svc.is_enabled.return_value = False
            MockService.return_value = mock_svc

            mock_db = AsyncMock()
            with pytest.raises(FeatureNotAvailableError):
                await dependency_fn(tenant_id=tenant_id, db=mock_db)


class TestRequireFeatureAdminDependency:
    """Tests for the require_feature() admin dependency function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_superuser_bypasses_check(self) -> None:
        """Superuser should always pass feature check."""
        from app.middleware.feature_check import require_feature

        dep = require_feature("blog_module")
        dependency_fn = dep.dependency

        mock_token = Mock()
        mock_token.is_superuser = True
        mock_token.permissions = []

        mock_db = AsyncMock()
        result = await dependency_fn(token=mock_token, db=mock_db)

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_platform_owner_bypasses_check(self) -> None:
        """Platform owner should bypass feature check."""
        from app.middleware.feature_check import require_feature

        dep = require_feature("cases_module")
        dependency_fn = dep.dependency

        mock_token = Mock()
        mock_token.is_superuser = False
        mock_token.permissions = ["platform:*"]

        mock_db = AsyncMock()
        result = await dependency_fn(token=mock_token, db=mock_db)

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disabled_feature_raises_403(self) -> None:
        """Regular user with disabled feature should get 403."""
        from app.middleware.feature_check import require_feature

        dep = require_feature("faq_module")
        dependency_fn = dep.dependency

        mock_token = Mock()
        mock_token.is_superuser = False
        mock_token.permissions = []
        mock_token.tenant_id = uuid4()

        with patch(
            "app.middleware.feature_check.FeatureFlagService"
        ) as MockService:
            mock_svc = AsyncMock()
            mock_svc.is_enabled.return_value = False
            MockService.return_value = mock_svc

            mock_db = AsyncMock()
            with pytest.raises(FeatureDisabledError) as exc_info:
                await dependency_fn(token=mock_token, db=mock_db)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["restriction_level"] == "organization"


class TestServicesModuleInAvailableFeatures:
    """Tests for services_module presence in AVAILABLE_FEATURES."""

    @pytest.mark.unit
    def test_services_module_exists(self) -> None:
        """services_module should be defined in AVAILABLE_FEATURES."""
        from app.modules.tenants.models import AVAILABLE_FEATURES

        assert "services_module" in AVAILABLE_FEATURES

    @pytest.mark.unit
    def test_services_module_has_required_fields(self) -> None:
        """services_module entry should have all required metadata."""
        from app.modules.tenants.models import AVAILABLE_FEATURES

        svc = AVAILABLE_FEATURES["services_module"]
        assert "title" in svc
        assert "title_ru" in svc
        assert "description" in svc
        assert "description_ru" in svc
        assert "category" in svc
        assert svc["category"] == "company"

    @pytest.mark.unit
    def test_all_feature_flags_have_metadata(self) -> None:
        """Every feature in AVAILABLE_FEATURES should have complete metadata."""
        from app.modules.tenants.models import AVAILABLE_FEATURES

        required_keys = {"title", "title_ru", "description", "description_ru", "category"}
        for name, meta in AVAILABLE_FEATURES.items():
            for key in required_keys:
                assert key in meta, f"Feature '{name}' missing '{key}'"
