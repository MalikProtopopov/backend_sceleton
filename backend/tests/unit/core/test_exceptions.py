"""Unit tests for exception classes -- RFC 7807 contract validation."""

from uuid import uuid4

import pytest

from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    DatabaseError,
    DefaultTenantConfigError,
    DuplicatePriceError,
    DuplicateRoleError,
    DuplicateTagError,
    ExternalServiceError,
    FeatureDisabledError,
    FeatureNotAvailableError,
    FileNotFoundInStorageError,
    InsufficientRoleError,
    InvalidCredentialsError,
    InvalidLocaleError,
    InvalidTenantIdError,
    InvalidTokenError,
    InvalidWebhookSecretError,
    LocaleDataMissingError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
    RoleInUseError,
    SlugAlreadyExistsError,
    SystemRoleModificationError,
    TenantHeaderRequiredError,
    TenantInactiveError,
    TenantNotFoundError,
    TenantRequiredError,
    TokenExpiredError,
    ValidationError,
    VersionConflictError,
)


def _assert_exc(exc, status_code: int, error_code: str, **extra_fields):
    """Helper: assert exception has correct status, error_code in type, and extra fields."""
    assert exc.status_code == status_code
    assert exc.detail["type"].endswith(f"/{error_code}")
    assert exc.detail["status"] == status_code
    assert "detail" in exc.detail  # message field
    for k, v in extra_fields.items():
        assert exc.detail.get(k) == v, f"Expected detail['{k}']={v!r}, got {exc.detail.get(k)!r}"


class TestAuthExceptions:

    @pytest.mark.unit
    def test_authentication_error(self):
        _assert_exc(AuthenticationError(), 401, "authentication_required")

    @pytest.mark.unit
    def test_invalid_credentials_error(self):
        _assert_exc(InvalidCredentialsError(), 401, "invalid_credentials")

    @pytest.mark.unit
    def test_token_expired_error(self):
        _assert_exc(TokenExpiredError(), 401, "token_expired")

    @pytest.mark.unit
    def test_invalid_token_error(self):
        _assert_exc(InvalidTokenError(), 401, "invalid_token")

    @pytest.mark.unit
    def test_permission_denied_error(self):
        err = PermissionDeniedError(required_permission="articles:create")
        _assert_exc(err, 403, "permission_denied", restriction_level="user", required_permission="articles:create")

    @pytest.mark.unit
    def test_insufficient_role_error(self):
        err = InsufficientRoleError(required_role="admin")
        _assert_exc(err, 403, "insufficient_role", restriction_level="user", required_role="admin")

    @pytest.mark.unit
    def test_tenant_inactive_error(self):
        _assert_exc(TenantInactiveError(), 403, "tenant_inactive")

    @pytest.mark.unit
    def test_feature_disabled_error(self):
        err = FeatureDisabledError("blog_module")
        _assert_exc(err, 403, "feature_disabled", restriction_level="organization", feature="blog_module", contact_admin=True)

    @pytest.mark.unit
    def test_feature_not_available_error(self):
        err = FeatureNotAvailableError("cases_module")
        _assert_exc(err, 404, "feature_not_available", feature="cases_module")
        assert "_hint" in err.detail

    @pytest.mark.unit
    def test_system_role_modification_error(self):
        _assert_exc(SystemRoleModificationError("delete"), 403, "system_role_protected", action="delete")

    @pytest.mark.unit
    def test_invalid_webhook_secret_error(self):
        _assert_exc(InvalidWebhookSecretError(), 401, "invalid_webhook_secret")


class TestResourceExceptions:

    @pytest.mark.unit
    def test_not_found_error(self):
        err = NotFoundError("Article", uuid4())
        _assert_exc(err, 404, "not_found", resource="Article")

    @pytest.mark.unit
    def test_already_exists_error(self):
        err = AlreadyExistsError("User", "email", "a@b.com")
        _assert_exc(err, 409, "already_exists", resource="User", field="email", value="a@b.com")

    @pytest.mark.unit
    def test_slug_already_exists_error(self):
        err = SlugAlreadyExistsError("my-slug", "ru")
        assert err.status_code == 409

    @pytest.mark.unit
    def test_version_conflict_error(self):
        err = VersionConflictError("Tenant", 5, 3)
        _assert_exc(err, 409, "version_conflict", current_version=5, provided_version=3, resource="Tenant")

    @pytest.mark.unit
    def test_duplicate_price_error(self):
        _assert_exc(DuplicatePriceError("ru", "RUB"), 409, "duplicate_price", locale="ru", currency="RUB")

    @pytest.mark.unit
    def test_duplicate_tag_error(self):
        _assert_exc(DuplicateTagError("my-tag", "en"), 409, "duplicate_tag", tag="my-tag", locale="en")

    @pytest.mark.unit
    def test_duplicate_role_error(self):
        _assert_exc(DuplicateRoleError("admin"), 409, "duplicate_role", role_name="admin")

    @pytest.mark.unit
    def test_role_in_use_error(self):
        _assert_exc(RoleInUseError("editor"), 409, "role_in_use", role_name="editor")

    @pytest.mark.unit
    def test_locale_data_missing_error(self):
        uid = uuid4()
        err = LocaleDataMissingError("Article", uid, "kz")
        _assert_exc(err, 500, "locale_data_missing", resource="Article", locale="kz")

    @pytest.mark.unit
    def test_tenant_not_found_error(self):
        tid = uuid4()
        _assert_exc(TenantNotFoundError(tid), 404, "tenant_not_found", tenant_id=str(tid))

    @pytest.mark.unit
    def test_file_not_found_in_storage_error(self):
        _assert_exc(FileNotFoundInStorageError("/images/x.png"), 404, "file_not_found", path="/images/x.png")


class TestTenantExceptions:

    @pytest.mark.unit
    def test_tenant_required_error(self):
        _assert_exc(TenantRequiredError(), 400, "tenant_required")

    @pytest.mark.unit
    def test_tenant_header_required_error(self):
        _assert_exc(TenantHeaderRequiredError(), 400, "tenant_header_required")

    @pytest.mark.unit
    def test_invalid_tenant_id_error(self):
        _assert_exc(InvalidTenantIdError("bad-uuid"), 400, "invalid_tenant_id", value="bad-uuid")

    @pytest.mark.unit
    def test_default_tenant_config_error(self):
        _assert_exc(DefaultTenantConfigError("No default tenant"), 500, "default_tenant_config_error")


class TestValidationExceptions:

    @pytest.mark.unit
    def test_validation_error(self):
        err = ValidationError("Invalid input", errors=[{"field": "name"}])
        _assert_exc(err, 400, "validation_error")
        assert err.detail["errors"] == [{"field": "name"}]

    @pytest.mark.unit
    def test_invalid_locale_error(self):
        err = InvalidLocaleError("xx", ["ru", "en"])
        assert err.status_code == 400


class TestRateLimitExceptions:

    @pytest.mark.unit
    def test_rate_limit_exceeded_error(self):
        err = RateLimitExceededError(retry_after=30)
        _assert_exc(err, 429, "rate_limit_exceeded", retry_after=30)

    @pytest.mark.unit
    def test_rate_limit_no_retry_after(self):
        err = RateLimitExceededError()
        _assert_exc(err, 429, "rate_limit_exceeded")


class TestExternalExceptions:

    @pytest.mark.unit
    def test_external_service_error(self):
        _assert_exc(ExternalServiceError("sendgrid"), 502, "external_service_error", service="sendgrid")

    @pytest.mark.unit
    def test_database_error(self):
        _assert_exc(DatabaseError(), 503, "database_error")
