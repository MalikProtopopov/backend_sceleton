"""Telegram integration exceptions."""

from app.core.exceptions import AppException


class TelegramError(AppException):
    """Base exception for Telegram integration errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "telegram_error",
    ):
        super().__init__(
            status_code=status_code,
            error_code=error_code,
            message=message,
        )


class TelegramIntegrationNotFoundError(TelegramError):
    """Raised when Telegram integration is not found for a tenant."""
    
    def __init__(self, tenant_id: str | None = None):
        message = "Telegram integration not found"
        if tenant_id:
            message = f"Telegram integration not found for tenant {tenant_id}"
        super().__init__(
            message=message,
            status_code=404,
            error_code="telegram_integration_not_found",
        )


class TelegramInvalidTokenError(TelegramError):
    """Raised when Telegram bot token is invalid."""
    
    def __init__(self, reason: str = "Invalid or expired token"):
        super().__init__(
            message=f"Invalid Telegram bot token: {reason}",
            status_code=400,
            error_code="telegram_invalid_token",
        )


class TelegramWebhookError(TelegramError):
    """Raised when webhook operation fails."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Telegram webhook error: {reason}",
            status_code=400,
            error_code="telegram_webhook_error",
        )


class TelegramApiError(TelegramError):
    """Raised when Telegram API call fails."""
    
    def __init__(self, method: str, reason: str):
        super().__init__(
            message=f"Telegram API error ({method}): {reason}",
            status_code=502,
            error_code="telegram_api_error",
        )


class TelegramNotConfiguredError(TelegramError):
    """Raised when Telegram integration is not properly configured."""
    
    def __init__(self, missing: str = "integration"):
        super().__init__(
            message=f"Telegram not configured: {missing}",
            status_code=400,
            error_code="telegram_not_configured",
        )

