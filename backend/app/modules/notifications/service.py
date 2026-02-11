"""Notification services for Email and Telegram."""

import httpx

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending email notifications."""

    async def send_welcome_email(
        self,
        to_email: str,
        first_name: str,
        tenant_name: str,
        admin_url: str | None = None,
    ) -> bool:
        """Send welcome email to newly created user.

        The email does NOT contain the password. The admin communicates
        the password to the user via another channel (phone, in person, etc.).

        Returns True if sent successfully.
        """
        platform_name = settings.app_name
        login_url = admin_url or f"{platform_name} Admin Panel"

        if settings.email_provider == "console":
            logger.info(
                "welcome_email",
                to=to_email,
                first_name=first_name,
                tenant_name=tenant_name,
            )
            return True

        subject = f"You've been invited to {tenant_name}"
        body = (
            f"Hello {first_name},\n\n"
            f"You have been granted access to {tenant_name} on {platform_name}.\n\n"
            f"Login URL: {login_url}\n"
            f"Email: {to_email}\n\n"
            f"Your password has been set by your administrator.\n"
            f"Please change it after your first login.\n\n"
            f"If you did not expect this email, please ignore it."
        )

        if settings.email_provider == "sendgrid":
            return await self._send_via_sendgrid(to_email, subject, body)
        elif settings.email_provider == "mailgun":
            return await self._send_via_mailgun(to_email, subject, body)

        return False

    async def send_password_reset_email(
        self,
        to_email: str,
        first_name: str,
        reset_token: str,
        reset_url: str | None = None,
    ) -> bool:
        """Send password reset email with token.

        Returns True if sent successfully.
        """
        if settings.email_provider == "console":
            logger.info(
                "password_reset_email",
                to=to_email,
                first_name=first_name,
                token=reset_token[:20] + "...",
            )
            return True

        link = reset_url or f"Reset token: {reset_token}"

        subject = "Password Reset Request"
        body = (
            f"Hello {first_name},\n\n"
            f"You have requested a password reset.\n\n"
            f"{link}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you did not request this, please ignore this email.\n"
        )

        if settings.email_provider == "sendgrid":
            return await self._send_via_sendgrid(to_email, subject, body)
        elif settings.email_provider == "mailgun":
            return await self._send_via_mailgun(to_email, subject, body)

        return False

    async def send_inquiry_notification(
        self,
        to_email: str,
        inquiry_name: str,
        inquiry_email: str | None,
        inquiry_phone: str | None,
        inquiry_message: str | None,
        inquiry_source: str | None = None,
    ) -> bool:
        """Send email notification about new inquiry.

        Returns True if sent successfully.
        """
        if settings.email_provider == "console":
            # Log to console in development
            logger.info(
                "email_notification",
                to=to_email,
                subject="Новая заявка",
                name=inquiry_name,
                email=inquiry_email,
                phone=inquiry_phone,
            )
            return True

        subject = f"Новая заявка от {inquiry_name}"
        body = self._build_inquiry_email_body(
            inquiry_name,
            inquiry_email,
            inquiry_phone,
            inquiry_message,
            inquiry_source,
        )

        if settings.email_provider == "sendgrid":
            return await self._send_via_sendgrid(to_email, subject, body)
        elif settings.email_provider == "mailgun":
            return await self._send_via_mailgun(to_email, subject, body)

        return False

    def _build_inquiry_email_body(
        self,
        name: str,
        email: str | None,
        phone: str | None,
        message: str | None,
        source: str | None,
    ) -> str:
        """Build email body for inquiry notification."""
        lines = [
            f"Имя: {name}",
        ]

        if email:
            lines.append(f"Email: {email}")
        if phone:
            lines.append(f"Телефон: {phone}")
        if message:
            lines.append(f"\nСообщение:\n{message}")
        if source:
            lines.append(f"\nИсточник: {source}")

        return "\n".join(lines)

    async def _send_via_sendgrid(
        self, to_email: str, subject: str, body: str
    ) -> bool:
        """Send email via SendGrid API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {settings.email_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {
                            "email": settings.email_from_address,
                            "name": settings.email_from_name,
                        },
                        "subject": subject,
                        "content": [{"type": "text/plain", "value": body}],
                    },
                )
                success = response.status_code in (200, 202)
                if not success:
                    logger.error(
                        "sendgrid_error",
                        status=response.status_code,
                        body=response.text,
                    )
                return success
        except Exception as e:
            logger.exception("sendgrid_exception", error=str(e))
            return False

    async def _send_via_mailgun(
        self, to_email: str, subject: str, body: str
    ) -> bool:
        """Send email via Mailgun API."""
        try:
            # Mailgun domain is part of the API key setup
            domain = settings.email_from_address.split("@")[1]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.mailgun.net/v3/{domain}/messages",
                    auth=("api", settings.email_api_key),
                    data={
                        "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                        "to": to_email,
                        "subject": subject,
                        "text": body,
                    },
                )
                success = response.status_code == 200
                if not success:
                    logger.error(
                        "mailgun_error",
                        status=response.status_code,
                        body=response.text,
                    )
                return success
        except Exception as e:
            logger.exception("mailgun_exception", error=str(e))
            return False


class TelegramService:
    """Service for sending Telegram notifications."""

    async def send_inquiry_notification(
        self,
        chat_id: str,
        inquiry_name: str,
        inquiry_email: str | None,
        inquiry_phone: str | None,
        inquiry_message: str | None,
        inquiry_source: str | None = None,
    ) -> bool:
        """Send Telegram notification about new inquiry.

        Returns True if sent successfully.
        """
        if not settings.telegram_bot_token:
            logger.warning("telegram_not_configured")
            return False

        message = self._build_inquiry_message(
            inquiry_name,
            inquiry_email,
            inquiry_phone,
            inquiry_message,
            inquiry_source,
        )

        return await self._send_message(chat_id, message)

    def _build_inquiry_message(
        self,
        name: str,
        email: str | None,
        phone: str | None,
        message: str | None,
        source: str | None,
    ) -> str:
        """Build Telegram message for inquiry notification."""
        lines = [
            "🆕 *Новая заявка*",
            "",
            f"👤 *Имя:* {self._escape_markdown(name)}",
        ]

        if email:
            lines.append(f"📧 *Email:* {self._escape_markdown(email)}")
        if phone:
            lines.append(f"📱 *Телефон:* {self._escape_markdown(phone)}")
        if message:
            lines.append(f"\n💬 *Сообщение:*\n{self._escape_markdown(message)}")
        if source:
            lines.append(f"\n🔗 *Источник:* {self._escape_markdown(source)}")

        return "\n".join(lines)

    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for Telegram MarkdownV2."""
        special_chars = ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        return text

    async def _send_message(self, chat_id: str, message: str) -> bool:
        """Send message to Telegram chat."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": "MarkdownV2",
                    },
                )
                success = response.status_code == 200
                if not success:
                    logger.error(
                        "telegram_error",
                        status=response.status_code,
                        body=response.text,
                    )
                return success
        except Exception as e:
            logger.exception("telegram_exception", error=str(e))
            return False


class NotificationService:
    """Unified notification service."""

    def __init__(self) -> None:
        self.email = EmailService()
        self.telegram = TelegramService()

    async def notify_inquiry(
        self,
        notification_email: str | None,
        telegram_chat_id: str | None,
        inquiry_name: str,
        inquiry_email: str | None,
        inquiry_phone: str | None,
        inquiry_message: str | None,
        inquiry_source: str | None = None,
    ) -> dict:
        """Send inquiry notifications via all configured channels.

        Returns dict with success status per channel.
        """
        results = {"email": False, "telegram": False}

        if notification_email:
            results["email"] = await self.email.send_inquiry_notification(
                to_email=notification_email,
                inquiry_name=inquiry_name,
                inquiry_email=inquiry_email,
                inquiry_phone=inquiry_phone,
                inquiry_message=inquiry_message,
                inquiry_source=inquiry_source,
            )

        if telegram_chat_id:
            results["telegram"] = await self.telegram.send_inquiry_notification(
                chat_id=telegram_chat_id,
                inquiry_name=inquiry_name,
                inquiry_email=inquiry_email,
                inquiry_phone=inquiry_phone,
                inquiry_message=inquiry_message,
                inquiry_source=inquiry_source,
            )

        logger.info(
            "notification_sent",
            email_sent=results["email"],
            telegram_sent=results["telegram"],
            inquiry_name=inquiry_name,
        )

        return results

