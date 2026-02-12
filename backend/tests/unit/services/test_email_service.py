"""Unit tests for EmailService provider routing."""

from unittest.mock import AsyncMock, patch

import pytest


class TestEmailServiceWelcome:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_console_provider_returns_true(self):
        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "console"
            mock_settings.email_from_address = "noreply@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_api_key = ""
            mock_settings.app_name = "TestApp"
            from app.modules.notifications.service import EmailService
            svc = EmailService()
            result = await svc.send_welcome_email("a@b.com", "John", "Acme")
            assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sendgrid_provider_calls_httpx(self):
        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "sendgrid"
            mock_settings.email_api_key = "SG.test_key"
            mock_settings.email_from_address = "noreply@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.app_name = "TestApp"
            from app.modules.notifications.service import EmailService
            svc = EmailService()
            with patch.object(
                svc, "_send_via_sendgrid",
                new_callable=AsyncMock,
                return_value=(True, None),
            ) as mock_send:
                result = await svc.send_welcome_email("a@b.com", "John", "Acme")
                assert result is True
                mock_send.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mailgun_provider_calls_httpx(self):
        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "mailgun"
            mock_settings.email_api_key = "mg.test_key"
            mock_settings.email_from_address = "noreply@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.app_name = "TestApp"
            from app.modules.notifications.service import EmailService
            svc = EmailService()
            with patch.object(
                svc, "_send_via_mailgun",
                new_callable=AsyncMock,
                return_value=(True, None),
            ) as mock_send:
                result = await svc.send_welcome_email("a@b.com", "John", "Acme")
                assert result is True
                mock_send.assert_called_once()


class TestEmailServicePasswordReset:

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reset_email_console_returns_true(self):
        with patch("app.modules.notifications.service.settings") as mock_settings:
            mock_settings.email_provider = "console"
            mock_settings.email_from_address = "noreply@test.com"
            mock_settings.email_from_name = "Test"
            mock_settings.email_api_key = ""
            mock_settings.app_name = "TestApp"
            from app.modules.notifications.service import EmailService
            svc = EmailService()
            result = await svc.send_password_reset_email("a@b.com", "John", "token123")
            assert result is True
