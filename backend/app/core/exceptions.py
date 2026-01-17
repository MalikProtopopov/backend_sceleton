"""Application exception hierarchy following RFC 7807 Problem Details."""

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception following RFC 7807.

    All custom exceptions should inherit from this class.
    Provides consistent error response format.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.error_detail = detail or {}

        super().__init__(
            status_code=status_code,
            detail={
                "type": f"https://api.cms.local/errors/{error_code}",
                "title": error_code.replace("_", " ").title(),
                "status": status_code,
                "detail": message,
                "instance": None,  # Will be set by exception handler
                **self.error_detail,
            },
        )


# ============================================================================
# Authentication & Authorization Exceptions (401, 403)
# ============================================================================


class AuthenticationError(AppException):
    """User is not authenticated."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="authentication_required",
            message=message,
        )


class InvalidCredentialsError(AppException):
    """Invalid login credentials."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="invalid_credentials",
            message=message,
        )


class TokenExpiredError(AppException):
    """JWT token has expired."""

    def __init__(self, message: str = "Token has expired") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="token_expired",
            message=message,
        )


class InvalidTokenError(AppException):
    """JWT token is invalid."""

    def __init__(self, message: str = "Invalid token") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="invalid_token",
            message=message,
        )


class PermissionDeniedError(AppException):
    """User lacks required permission."""

    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: str | None = None,
    ) -> None:
        detail = {}
        if required_permission:
            detail["required_permission"] = required_permission

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="permission_denied",
            message=message,
            detail=detail,
        )


class InsufficientRoleError(AppException):
    """User role is insufficient."""

    def __init__(
        self,
        message: str = "Insufficient role privileges",
        required_role: str | None = None,
    ) -> None:
        detail = {}
        if required_role:
            detail["required_role"] = required_role

        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="insufficient_role",
            message=message,
            detail=detail,
        )


class FeatureDisabledError(AppException):
    """Feature is disabled for this tenant."""

    def __init__(self, feature_name: str) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="feature_disabled",
            message=f"Feature '{feature_name}' is not enabled for this tenant",
            detail={"feature": feature_name},
        )


# ============================================================================
# Resource Exceptions (404, 409)
# ============================================================================


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(
        self,
        resource: str,
        identifier: str | UUID | None = None,
    ) -> None:
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with id '{identifier}' not found"

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="not_found",
            message=message,
            detail={"resource": resource},
        )


class AlreadyExistsError(AppException):
    """Resource already exists (conflict)."""

    def __init__(
        self,
        resource: str,
        field: str,
        value: str,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="already_exists",
            message=f"{resource} with {field}='{value}' already exists",
            detail={"resource": resource, "field": field, "value": value},
        )


class SlugAlreadyExistsError(AlreadyExistsError):
    """Slug already exists for this locale."""

    def __init__(self, slug: str, locale: str | None = None) -> None:
        detail = {"slug": slug}
        message = f"Slug '{slug}' already exists"
        if locale:
            detail["locale"] = locale
            message = f"Slug '{slug}' already exists for locale '{locale}'"

        super().__init__(
            resource="Content",
            field="slug",
            value=slug,
        )
        self.error_detail.update(detail)


class VersionConflictError(AppException):
    """Optimistic locking conflict - resource was modified."""

    def __init__(
        self,
        resource: str,
        current_version: int,
        provided_version: int,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="version_conflict",
            message=f"{resource} was modified by another user. Please refresh and try again.",
            detail={
                "resource": resource,
                "current_version": current_version,
                "provided_version": provided_version,
            },
        )


class DuplicatePriceError(AppException):
    """Service price for this locale/currency already exists."""

    def __init__(self, locale: str, currency: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="duplicate_price",
            message=f"Price for locale '{locale}' and currency '{currency}' already exists",
            detail={"locale": locale, "currency": currency},
        )


class DuplicateTagError(AppException):
    """Service tag for this locale already exists."""

    def __init__(self, tag: str, locale: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="duplicate_tag",
            message=f"Tag '{tag}' for locale '{locale}' already exists",
            detail={"tag": tag, "locale": locale},
        )


class DuplicateRoleError(AppException):
    """Role with this name already exists."""

    def __init__(self, name: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="duplicate_role",
            message=f"Role with name '{name}' already exists",
            detail={"role_name": name},
        )


class SystemRoleModificationError(AppException):
    """Cannot modify or delete system roles."""

    def __init__(self, action: str = "modify") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="system_role_protected",
            message=f"Cannot {action} system roles",
            detail={"action": action},
        )


class RoleInUseError(AppException):
    """Cannot delete role that is assigned to users."""

    def __init__(self, role_name: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="role_in_use",
            message="Cannot delete role that is assigned to users",
            detail={"role_name": role_name},
        )


class LocaleDataMissingError(AppException):
    """Locale data not found for entity."""

    def __init__(self, resource: str, resource_id: UUID, locale: str) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="locale_data_missing",
            message=f"No locale data found for {resource} {resource_id}",
            detail={"resource": resource, "resource_id": str(resource_id), "locale": locale},
        )


class TenantRequiredError(AppException):
    """Tenant ID is required in multi-tenant mode."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="tenant_required",
            message="tenant_id parameter is required in multi-tenant mode",
        )


class TenantHeaderRequiredError(AppException):
    """X-Tenant-ID header is required in multi-tenant mode."""

    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="tenant_header_required",
            message="X-Tenant-ID header is required (single_tenant_mode=false)",
        )


class InvalidTenantIdError(AppException):
    """Invalid tenant ID format."""

    def __init__(self, value: str) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="invalid_tenant_id",
            message="Invalid X-Tenant-ID format",
            detail={"value": value},
        )


class TenantNotFoundError(AppException):
    """Tenant not found or inactive."""

    def __init__(self, tenant_id: UUID | str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="tenant_not_found",
            message="Tenant not found or inactive",
            detail={"tenant_id": str(tenant_id)},
        )


class DefaultTenantConfigError(AppException):
    """Default tenant configuration error in single-tenant mode."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="default_tenant_config_error",
            message=reason,
        )


class InvalidWebhookSecretError(AppException):
    """Invalid or missing webhook secret token."""

    def __init__(self, reason: str = "Invalid secret token") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="invalid_webhook_secret",
            message=reason,
        )


class FileNotFoundInStorageError(AppException):
    """File not found in storage (S3)."""

    def __init__(self, path: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="file_not_found",
            message="File not found",
            detail={"path": path},
        )


# ============================================================================
# Validation Exceptions (400, 422)
# ============================================================================


class ValidationError(AppException):
    """Request validation error."""

    def __init__(
        self,
        message: str,
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="validation_error",
            message=message,
            detail={"errors": errors or []},
        )


class InvalidLocaleError(ValidationError):
    """Invalid or unsupported locale."""

    def __init__(self, locale: str, supported_locales: list[str]) -> None:
        super().__init__(
            message=f"Locale '{locale}' is not supported",
            errors=[
                {
                    "field": "locale",
                    "value": locale,
                    "supported": supported_locales,
                }
            ],
        )


# ============================================================================
# Rate Limiting Exceptions (429)
# ============================================================================


class RateLimitExceededError(AppException):
    """Too many requests."""

    def __init__(
        self,
        message: str = "Too many requests",
        retry_after: int | None = None,
    ) -> None:
        detail = {}
        if retry_after:
            detail["retry_after"] = retry_after

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="rate_limit_exceeded",
            message=message,
            detail=detail,
        )


# ============================================================================
# External Service Exceptions (502, 503)
# ============================================================================


class ExternalServiceError(AppException):
    """External service (email, S3, etc.) error."""

    def __init__(
        self,
        service: str,
        message: str = "External service unavailable",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="external_service_error",
            message=message,
            detail={"service": service},
        )


class DatabaseError(AppException):
    """Database connection or query error."""

    def __init__(self, message: str = "Database error occurred") -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="database_error",
            message=message,
        )

