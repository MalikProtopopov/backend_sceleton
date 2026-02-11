"""Telegram notifier for sending inquiry notifications.

Sends formatted notifications to site owners when new inquiries are received.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.leads.models import Inquiry
from app.modules.leads.schemas import CUSTOM_FIELDS_LABELS
from app.modules.telegram.service import TelegramIntegrationService

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Service for sending Telegram notifications about inquiries."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._service: TelegramIntegrationService | None = None
    
    @property
    def service(self) -> TelegramIntegrationService:
        """Lazy initialization of Telegram service."""
        if self._service is None:
            self._service = TelegramIntegrationService(self.db)
        return self._service
    
    async def send_new_inquiry(
        self,
        tenant_id: UUID,
        inquiry: Inquiry,
    ) -> bool:
        """Send notification about new inquiry.
        
        Args:
            tenant_id: Tenant UUID
            inquiry: Inquiry model instance
            
        Returns:
            True if notification sent successfully
        """
        try:
            message = self._format_inquiry_message(inquiry)
            
            success = await self.service.send_notification(
                tenant_id=tenant_id,
                text=message,
                parse_mode="HTML",
            )
            
            if success:
                logger.info(
                    f"Sent Telegram notification for inquiry {inquiry.id} "
                    f"to tenant {tenant_id}"
                )
            else:
                logger.debug(
                    f"Telegram notification not sent for inquiry {inquiry.id} "
                    f"(integration not configured or disabled)"
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Failed to send Telegram notification for inquiry {inquiry.id}: {e}"
            )
            return False
    
    def _format_inquiry_message(self, inquiry: Inquiry) -> str:
        """Format inquiry data as HTML message.
        
        Args:
            inquiry: Inquiry model instance
            
        Returns:
            Formatted HTML message
        """
        lines = [
            "📝 <b>Новая заявка с сайта</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]
        
        # Contact info
        lines.append(f"👤 <b>Имя:</b> {self._escape_html(inquiry.name)}")
        
        if inquiry.email:
            lines.append(f"📧 <b>Email:</b> {self._escape_html(inquiry.email)}")
        
        if inquiry.phone:
            lines.append(f"📞 <b>Телефон:</b> {self._escape_html(inquiry.phone)}")
        
        if inquiry.company:
            lines.append(f"🏢 <b>Компания:</b> {self._escape_html(inquiry.company)}")
        
        # Telegram from custom_fields (contact-level, show near other contacts)
        tg_handle = self._get_custom_field(inquiry, "telegram")
        if tg_handle:
            lines.append(f"✈️ <b>Telegram:</b> {self._escape_html(tg_handle)}")
        
        # Message
        if inquiry.message:
            lines.append("")
            lines.append("💬 <b>Сообщение:</b>")
            # Truncate long messages
            message = inquiry.message
            if len(message) > 1000:
                message = message[:1000] + "..."
            lines.append(self._escape_html(message))
        
        # Custom fields (MVP brief and others)
        custom_lines = self._format_custom_fields(inquiry)
        if custom_lines:
            lines.append("")
            lines.append("📋 <b>Детали заявки</b>")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━")
            lines.extend(custom_lines)
        
        # Source info
        source_info = []
        
        if inquiry.utm_source:
            source_info.append(f"utm_source: {inquiry.utm_source}")
        if inquiry.utm_campaign:
            source_info.append(f"utm_campaign: {inquiry.utm_campaign}")
        if inquiry.page_path:
            source_info.append(f"страница: {inquiry.page_path}")
        if inquiry.device_type:
            source_info.append(f"устройство: {inquiry.device_type}")
        
        if source_info:
            lines.append("")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━")
            lines.append(f"🔗 <i>{' | '.join(source_info)}</i>")
        
        return "\n".join(lines)
    
    def _get_custom_field(self, inquiry: Inquiry, key: str) -> str | None:
        """Get a value from custom_fields by key."""
        if not inquiry.custom_fields or not isinstance(inquiry.custom_fields, dict):
            return None
        value = inquiry.custom_fields.get(key)
        if value is None or value == "":
            return None
        return str(value)
    
    # Keys already shown elsewhere (contacts) or not useful in Telegram
    _SKIP_KEYS = {"telegram", "consent"}
    
    def _format_custom_fields(self, inquiry: Inquiry) -> list[str]:
        """Format custom_fields as labeled lines for Telegram message.
        
        Only includes fields that have a non-empty value.
        Uses human-readable labels from CUSTOM_FIELDS_LABELS.
        """
        if not inquiry.custom_fields or not isinstance(inquiry.custom_fields, dict):
            return []
        
        lines: list[str] = []
        for key, value in inquiry.custom_fields.items():
            if key in self._SKIP_KEYS:
                continue
            if value is None or value == "" or value == []:
                continue
            
            label = CUSTOM_FIELDS_LABELS.get(key, key)
            
            if isinstance(value, list):
                display = ", ".join(str(v) for v in value)
            elif isinstance(value, bool):
                display = "Да" if value else "Нет"
            else:
                display = str(value)
            
            # Truncate very long values
            if len(display) > 500:
                display = display[:500] + "..."
            
            lines.append(f"• <b>{self._escape_html(label)}:</b> {self._escape_html(display)}")
        
        return lines
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for HTML
        """
        if not text:
            return ""
        
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )


# Factory function for creating notifier with db session
def get_telegram_notifier(db: AsyncSession) -> TelegramNotifier:
    """Create TelegramNotifier instance.
    
    Args:
        db: Database session
        
    Returns:
        TelegramNotifier instance
    """
    return TelegramNotifier(db)

