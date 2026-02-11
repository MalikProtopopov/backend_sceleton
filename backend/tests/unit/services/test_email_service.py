"""Unit tests for EmailService — welcome email, password reset email."""

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.notifications.service import EmailService


class TestEmailServiceWelcome:
    """Tests for EmailService.send_welcome_email."""

    @pytest.fixture
    def email_service(self) -> EmailService:
        return EmailService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_welcome_email_console_provider(self, email_service: EmailService) -> None:
        """Console provider should log and return True (no password in log)."""
        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "console"
            mock_settings.app_name = "TestApp"

            result = await email_service.send_welcome_email(
                to_email="user@example.com",
                first_name="John",
                tenant_name="Acme Corp",
            )

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_welcome_email_sendgrid(self, email_service: EmailService) -> None:
        """SendGrid provider should POST to API."""
        import respx
        import httpx

        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "sendgrid"
            mock_settings.email_api_key = "test-api-key"
            mock_settings.email_from_address = "noreply@test.com"
            mock_settings.email_from_name = "Test App"
            mock_settings.app_name = "TestApp"

            with respx.mock:
                respx.post("https://api.sendgrid.com/v3/mail/send").respond(202)
                result = await email_service.send_welcome_email(
                    to_email="user@example.com",
                    first_name="John",
                    tenant_name="Acme Corp",
                )

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_welcome_email_failure_returns_false(self, email_service: EmailService) -> None:
        """SendGrid HTTP error should return False."""
        import respx

        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "sendgrid"
            mock_settings.email_api_key = "test-api-key"
            mock_settings.email_from_address = "noreply@test.com"
            mock_settings.email_from_name = "Test App"
            mock_settings.app_name = "TestApp"

            with respx.mock:
                respx.post("https://api.sendgrid.com/v3/mail/send").respond(500)
                result = await email_service.send_welcome_email(
                    to_email="user@example.com",
                    first_name="John",
                    tenant_name="Acme Corp",
                )

        assert result is False


class TestEmailServicePasswordReset:
    """Tests for EmailService.send_password_reset_email."""

    @pytest.fixture
    def email_service(self) -> EmailService:
        return EmailService()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_password_reset_email_console_provider(self, email_service: EmailService) -> None:
        """Console provider should log and return True."""
        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "console"

            result = await email_service.send_password_reset_email(
                to_email="user@example.com",
                first_name="John",
                reset_token="some-long-jwt-token-value-here",
            )

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_send_password_reset_email_sendgrid(self, email_service: EmailService) -> None:
        """SendGrid provider should POST to API."""
        import respx

        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "sendgrid"
            mock_settings.email_api_key = "test-api-key"
            mock_settings.email_from_address = "noreply@test.com"
            mock_settings.email_from_name = "Test App"

            with respx.mock:
                respx.post("https://api.sendgrid.com/v3/mail/send").respond(202)
                result = await email_service.send_password_reset_email(
                    to_email="user@example.com",
                    first_name="John",
                    reset_token="jwt-token-here",
                )

        assert result is True
