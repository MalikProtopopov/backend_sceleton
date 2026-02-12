"""Notification services for Email and Telegram.

EmailService is tenant-aware: it loads per-tenant SMTP/email configuration
from TenantSettings and falls back to global settings when not configured.
Every send attempt is logged to the email_logs table.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EmailConfig:
    """Resolved email configuration (tenant-level or global fallback)."""

    provider: str  # smtp, sendgrid, mailgun, console
    from_address: str
    from_name: str
    # SMTP-specific
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    # API-key based providers (SendGrid / Mailgun)
    api_key: str | None = None


class EmailService:
    """Service for sending email notifications.

    Tenant-aware: accepts an optional db session and tenant_id.
    When tenant_id is provided, loads per-tenant email config from TenantSettings.
    Falls back to global settings (config.py / env vars) when no tenant config exists.
    """

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public send methods
    # ------------------------------------------------------------------

    async def send_welcome_email(
        self,
        to_email: str,
        first_name: str,
        tenant_name: str,
        admin_url: str | None = None,
        tenant_id: UUID | None = None,
    ) -> bool:
        """Send welcome email to newly created user.

        The email does NOT contain the password. The admin communicates
        the password to the user via another channel (phone, in person, etc.).
        """
        platform_name = settings.app_name
        login_url = admin_url or f"{platform_name} Admin Panel"

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

        return await self._send(
            to_email=to_email,
            subject=subject,
            body=body,
            email_type="welcome",
            tenant_id=tenant_id,
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        first_name: str,
        reset_token: str,
        reset_url: str | None = None,
        tenant_id: UUID | None = None,
    ) -> bool:
        """Send password reset email with token."""
        link = reset_url or f"Reset token: {reset_token}"

        subject = "Password Reset Request"
        body = (
            f"Hello {first_name},\n\n"
            f"You have requested a password reset.\n\n"
            f"{link}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you did not request this, please ignore this email.\n"
        )

        return await self._send(
            to_email=to_email,
            subject=subject,
            body=body,
            email_type="password_reset",
            tenant_id=tenant_id,
        )

    async def send_inquiry_notification(
        self,
        to_email: str,
        inquiry_name: str,
        inquiry_email: str | None,
        inquiry_phone: str | None,
        inquiry_message: str | None,
        inquiry_source: str | None = None,
        tenant_id: UUID | None = None,
    ) -> bool:
        """Send email notification about new inquiry."""
        subject = f"Новая заявка от {inquiry_name}"
        body = self._build_inquiry_email_body(
            inquiry_name,
            inquiry_email,
            inquiry_phone,
            inquiry_message,
            inquiry_source,
        )

        return await self._send(
            to_email=to_email,
            subject=subject,
            body=body,
            email_type="inquiry",
            tenant_id=tenant_id,
        )

    async def send_test_email(
        self,
        to_email: str,
        tenant_id: UUID,
    ) -> tuple[bool, str | None]:
        """Send a test email using tenant's email configuration.

        Returns (success, error_message).
        """
        config = await self._resolve_config(tenant_id)

        subject = "Test Email - Configuration Verified"
        body = (
            "This is a test email to verify your email configuration.\n\n"
            f"Provider: {config.provider}\n"
            f"From: {config.from_name} <{config.from_address}>\n\n"
            "If you received this email, your configuration is working correctly."
        )

        success, error = await self._dispatch(
            config=config,
            to_email=to_email,
            subject=subject,
            body=body,
        )

        # Log the attempt
        await self._log_email(
            tenant_id=tenant_id,
            to_email=to_email,
            subject=subject,
            email_type="test",
            provider=config.provider,
            success=success,
            error_message=error,
        )

        return success, error

    # ------------------------------------------------------------------
    # Internal: unified send with config resolution and logging
    # ------------------------------------------------------------------

    async def _send(
        self,
        to_email: str,
        subject: str,
        body: str,
        email_type: str,
        tenant_id: UUID | None = None,
    ) -> bool:
        """Resolve config, send email, and log the attempt."""
        config = await self._resolve_config(tenant_id)

        success, error = await self._dispatch(
            config=config,
            to_email=to_email,
            subject=subject,
            body=body,
        )

        # Log the attempt (best-effort, don't fail the send)
        try:
            await self._log_email(
                tenant_id=tenant_id,
                to_email=to_email,
                subject=subject,
                email_type=email_type,
                provider=config.provider,
                success=success,
                error_message=error,
            )
        except Exception:
            logger.warning("email_log_failed", to=to_email, email_type=email_type)

        return success

    async def _dispatch(
        self,
        config: EmailConfig,
        to_email: str,
        subject: str,
        body: str,
    ) -> tuple[bool, str | None]:
        """Dispatch email via the configured provider.

        Returns (success, error_message).
        """
        if config.provider == "console":
            logger.info(
                "email_console",
                to=to_email,
                subject=subject,
                from_addr=config.from_address,
            )
            return True, None

        try:
            if config.provider == "smtp":
                await self._send_via_smtp(to_email, subject, body, config)
                return True, None
            elif config.provider == "sendgrid":
                return await self._send_via_sendgrid(to_email, subject, body, config)
            elif config.provider == "mailgun":
                return await self._send_via_mailgun(to_email, subject, body, config)
            else:
                return False, f"Unknown provider: {config.provider}"
        except Exception as e:
            logger.exception("email_send_error", provider=config.provider, error=str(e))
            return False, str(e)

    # ------------------------------------------------------------------
    # Config resolution
    # ------------------------------------------------------------------

    async def _resolve_config(self, tenant_id: UUID | None = None) -> EmailConfig:
        """Resolve email configuration: tenant-specific or global fallback."""
        if tenant_id and self.db:
            try:
                from app.modules.tenants.models import TenantSettings

                stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
                result = await self.db.execute(stmt)
                ts = result.scalar_one_or_none()

                if ts and ts.email_provider:
                    # Tenant has its own email config
                    return self._build_tenant_config(ts)
            except Exception:
                logger.warning("tenant_email_config_fallback", tenant_id=str(tenant_id))

        # Global fallback
        return EmailConfig(
            provider=settings.email_provider,
            from_address=settings.email_from_address,
            from_name=settings.email_from_name,
            api_key=settings.email_api_key or None,
        )

    def _build_tenant_config(self, ts) -> EmailConfig:
        """Build EmailConfig from TenantSettings, decrypting secrets."""
        from app.core.encryption import get_encryption_service

        enc = get_encryption_service()

        smtp_password = None
        if ts.smtp_password_encrypted:
            try:
                smtp_password = enc.decrypt(ts.smtp_password_encrypted)
            except Exception:
                logger.warning("smtp_password_decrypt_failed", tenant_id=str(ts.tenant_id))

        api_key = None
        if ts.email_api_key_encrypted:
            try:
                api_key = enc.decrypt(ts.email_api_key_encrypted)
            except Exception:
                logger.warning("email_api_key_decrypt_failed", tenant_id=str(ts.tenant_id))

        return EmailConfig(
            provider=ts.email_provider,
            from_address=ts.email_from_address or settings.email_from_address,
            from_name=ts.email_from_name or settings.email_from_name,
            smtp_host=ts.smtp_host,
            smtp_port=ts.smtp_port or 587,
            smtp_user=ts.smtp_user,
            smtp_password=smtp_password,
            smtp_use_tls=ts.smtp_use_tls,
            api_key=api_key,
        )

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    async def _send_via_smtp(
        self,
        to_email: str,
        subject: str,
        body: str,
        config: EmailConfig,
    ) -> None:
        """Send email via SMTP using aiosmtplib.

        Raises on failure (caller catches and converts to (False, error)).
        """
        import aiosmtplib

        if not config.smtp_host:
            raise ValueError("SMTP host is not configured")

        msg = MIMEMultipart()
        msg["From"] = f"{config.from_name} <{config.from_address}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_user,
            password=config.smtp_password,
            start_tls=config.smtp_use_tls,
        )

    async def _send_via_sendgrid(
        self, to_email: str, subject: str, body: str, config: EmailConfig
    ) -> tuple[bool, str | None]:
        """Send email via SendGrid API."""
        if not config.api_key:
            return False, "SendGrid API key is not configured"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {
                            "email": config.from_address,
                            "name": config.from_name,
                        },
                        "subject": subject,
                        "content": [{"type": "text/plain", "value": body}],
                    },
                )
                if response.status_code in (200, 202):
                    return True, None
                error = f"SendGrid {response.status_code}: {response.text}"
                logger.error("sendgrid_error", status=response.status_code, body=response.text)
                return False, error
        except Exception as e:
            logger.exception("sendgrid_exception", error=str(e))
            return False, str(e)

    async def _send_via_mailgun(
        self, to_email: str, subject: str, body: str, config: EmailConfig
    ) -> tuple[bool, str | None]:
        """Send email via Mailgun API."""
        if not config.api_key:
            return False, "Mailgun API key is not configured"

        try:
            domain = config.from_address.split("@")[1]

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.mailgun.net/v3/{domain}/messages",
                    auth=("api", config.api_key),
                    data={
                        "from": f"{config.from_name} <{config.from_address}>",
                        "to": to_email,
                        "subject": subject,
                        "text": body,
                    },
                )
                if response.status_code == 200:
                    return True, None
                error = f"Mailgun {response.status_code}: {response.text}"
                logger.error("mailgun_error", status=response.status_code, body=response.text)
                return False, error
        except Exception as e:
            logger.exception("mailgun_exception", error=str(e))
            return False, str(e)

    # ------------------------------------------------------------------
    # Email body builders
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Email logging
    # ------------------------------------------------------------------

    async def _log_email(
        self,
        tenant_id: UUID | None,
        to_email: str,
        subject: str,
        email_type: str,
        provider: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Record an email send attempt in email_logs table."""
        if not self.db or not tenant_id:
            return  # Can't log without db session or tenant context

        from app.modules.notifications.models import EmailLog

        log_entry = EmailLog(
            tenant_id=tenant_id,
            to_email=to_email,
            subject=subject[:500],  # Truncate to column max
            email_type=email_type,
            provider=provider,
            status="sent" if success else ("console" if provider == "console" else "failed"),
            error_message=error_message[:2000] if error_message else None,
        )
        self.db.add(log_entry)
        try:
            await self.db.flush()
        except Exception:
            logger.warning("email_log_flush_failed", to=to_email, email_type=email_type)


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

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.email = EmailService(db=db)
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
        tenant_id: UUID | None = None,
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
                tenant_id=tenant_id,
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
