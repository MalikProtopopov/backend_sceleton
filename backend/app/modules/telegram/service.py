"""Telegram integration service.

Handles bot validation, webhook management, and message sending.
"""

import logging
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.encryption import (
    EncryptionService,
    generate_secret,
    mask_value,
)
from app.modules.telegram.exceptions import (
    TelegramApiError,
    TelegramIntegrationNotFoundError,
    TelegramInvalidTokenError,
    TelegramNotConfiguredError,
    TelegramWebhookError,
)
from app.modules.telegram.models import TelegramIntegration
from app.modules.telegram.schemas import (
    TelegramIntegrationCreate,
    TelegramIntegrationUpdate,
)

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}"
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_TIMEOUT = httpx.Timeout(
    timeout=30.0,
    connect=5.0,
    read=25.0,
    write=10.0,
)


class TelegramIntegrationService:
    """Service for managing Telegram bot integrations."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._encryption = EncryptionService()
    
    # =========================================================================
    # Integration CRUD
    # =========================================================================
    
    async def get_integration(self, tenant_id: UUID) -> TelegramIntegration | None:
        """Get Telegram integration for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            TelegramIntegration or None if not found
        """
        stmt = select(TelegramIntegration).where(
            TelegramIntegration.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_integration_or_raise(self, tenant_id: UUID) -> TelegramIntegration:
        """Get Telegram integration or raise error.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            TelegramIntegration
            
        Raises:
            TelegramIntegrationNotFoundError: If not found
        """
        integration = await self.get_integration(tenant_id)
        if not integration:
            raise TelegramIntegrationNotFoundError(str(tenant_id))
        return integration
    
    async def get_integration_by_secret(
        self,
        webhook_secret: str,
    ) -> TelegramIntegration | None:
        """Get integration by webhook secret.
        
        Args:
            webhook_secret: Webhook secret from URL
            
        Returns:
            TelegramIntegration or None
        """
        stmt = select(TelegramIntegration).where(
            TelegramIntegration.webhook_secret == webhook_secret
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_integration(
        self,
        tenant_id: UUID,
        data: TelegramIntegrationCreate,
    ) -> TelegramIntegration:
        """Create Telegram integration for a tenant.
        
        Validates bot token with Telegram API before creating.
        
        Args:
            tenant_id: Tenant UUID
            data: Integration data
            
        Returns:
            Created TelegramIntegration
            
        Raises:
            TelegramInvalidTokenError: If token is invalid
        """
        # Validate token and get bot info
        bot_info = await self._get_bot_info(data.bot_token)
        if not bot_info:
            raise TelegramInvalidTokenError("Could not validate token with Telegram")
        
        # Check if integration already exists
        existing = await self.get_integration(tenant_id)
        if existing:
            # Update existing instead of creating new
            return await self.update_integration(
                tenant_id,
                TelegramIntegrationUpdate(
                    bot_token=data.bot_token,
                    owner_chat_id=data.owner_chat_id,
                    welcome_message=data.welcome_message,
                ),
            )
        
        # Encrypt token
        encrypted_token = self._encryption.encrypt(data.bot_token)
        
        # Generate webhook secret
        webhook_secret = generate_secret(32)
        
        integration = TelegramIntegration(
            tenant_id=tenant_id,
            bot_token_encrypted=encrypted_token,
            bot_username=bot_info.get("username"),
            owner_chat_id=data.owner_chat_id,
            webhook_secret=webhook_secret,
            welcome_message=data.welcome_message,
            is_active=True,
        )
        
        self.db.add(integration)
        await self.db.commit()
        await self.db.refresh(integration)
        
        logger.info(
            f"Created Telegram integration for tenant {tenant_id}, "
            f"bot @{bot_info.get('username')}"
        )
        
        return integration
    
    async def update_integration(
        self,
        tenant_id: UUID,
        data: TelegramIntegrationUpdate,
    ) -> TelegramIntegration:
        """Update Telegram integration.
        
        Args:
            tenant_id: Tenant UUID
            data: Update data
            
        Returns:
            Updated TelegramIntegration
        """
        integration = await self.get_integration_or_raise(tenant_id)
        
        # If bot token is being updated, validate it first
        if data.bot_token is not None:
            bot_info = await self._get_bot_info(data.bot_token)
            if not bot_info:
                raise TelegramInvalidTokenError("Could not validate new token")
            
            integration.bot_token_encrypted = self._encryption.encrypt(data.bot_token)
            integration.bot_username = bot_info.get("username")
            
            # Webhook needs to be re-registered with new token
            if integration.is_webhook_active:
                integration.is_webhook_active = False
                integration.webhook_url = None
        
        if data.owner_chat_id is not None:
            integration.owner_chat_id = data.owner_chat_id
        
        if data.is_active is not None:
            integration.is_active = data.is_active
        
        if data.welcome_message is not None:
            integration.welcome_message = data.welcome_message
        
        await self.db.commit()
        await self.db.refresh(integration)
        
        logger.info(f"Updated Telegram integration for tenant {tenant_id}")
        
        return integration
    
    async def delete_integration(self, tenant_id: UUID) -> None:
        """Delete Telegram integration.
        
        Removes webhook from Telegram before deleting.
        
        Args:
            tenant_id: Tenant UUID
        """
        integration = await self.get_integration(tenant_id)
        if not integration:
            return
        
        # Remove webhook if active
        if integration.is_webhook_active:
            try:
                bot_token = self._decrypt_token(integration)
                await self._delete_webhook(bot_token)
            except Exception as e:
                logger.warning(f"Failed to remove webhook on delete: {e}")
        
        await self.db.delete(integration)
        await self.db.commit()
        
        logger.info(f"Deleted Telegram integration for tenant {tenant_id}")
    
    # =========================================================================
    # Webhook Management
    # =========================================================================
    
    async def set_webhook(
        self,
        tenant_id: UUID,
        webhook_url: str,
    ) -> bool:
        """Set webhook URL for the bot.
        
        Args:
            tenant_id: Tenant UUID
            webhook_url: HTTPS URL for webhook
            
        Returns:
            True if successful
        """
        integration = await self.get_integration_or_raise(tenant_id)
        bot_token = self._decrypt_token(integration)
        
        success = await self._set_webhook(
            bot_token,
            webhook_url,
            integration.webhook_secret,
        )
        
        if success:
            integration.webhook_url = webhook_url
            integration.is_webhook_active = True
            await self.db.commit()
            logger.info(f"Set webhook for tenant {tenant_id}: {webhook_url}")
        
        return success
    
    async def remove_webhook(self, tenant_id: UUID) -> bool:
        """Remove webhook for the bot.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if successful
        """
        integration = await self.get_integration_or_raise(tenant_id)
        bot_token = self._decrypt_token(integration)
        
        success = await self._delete_webhook(bot_token)
        
        if success:
            integration.webhook_url = None
            integration.is_webhook_active = False
            await self.db.commit()
            logger.info(f"Removed webhook for tenant {tenant_id}")
        
        return success
    
    def get_webhook_url(self, integration: TelegramIntegration) -> str | None:
        """Generate webhook URL for integration.
        
        Args:
            integration: TelegramIntegration instance
            
        Returns:
            Full webhook URL or None if PUBLIC_API_URL not configured
        """
        if not settings.public_api_url:
            return None
        
        base_url = settings.public_api_url.rstrip("/")
        return f"{base_url}{settings.api_prefix}/telegram/webhook/{integration.webhook_secret}"
    
    # =========================================================================
    # Message Sending
    # =========================================================================
    
    async def send_test_message(
        self,
        tenant_id: UUID,
        chat_id: int | None = None,
    ) -> bool:
        """Send a test message to verify configuration.
        
        Args:
            tenant_id: Tenant UUID
            chat_id: Override chat ID (uses owner_chat_id if not provided)
            
        Returns:
            True if message sent successfully
        """
        integration = await self.get_integration_or_raise(tenant_id)
        
        target_chat_id = chat_id or integration.owner_chat_id
        if not target_chat_id:
            raise TelegramNotConfiguredError("owner_chat_id not set")
        
        bot_token = self._decrypt_token(integration)
        text = (
            "✅ <b>Тестовое сообщение</b>\n\n"
            "Telegram интеграция настроена успешно!\n"
            "Вы будете получать уведомления о новых заявках."
        )
        
        return await self._send_message(
            bot_token,
            target_chat_id,
            text,
            parse_mode="HTML",
        )
    
    async def send_notification(
        self,
        tenant_id: UUID,
        text: str,
        parse_mode: str = "HTML",
    ) -> bool:
        """Send notification to owner.
        
        Args:
            tenant_id: Tenant UUID
            text: Message text
            parse_mode: HTML or Markdown
            
        Returns:
            True if sent successfully
        """
        integration = await self.get_integration(tenant_id)
        
        if not integration:
            logger.debug(f"No Telegram integration for tenant {tenant_id}")
            return False
        
        if not integration.is_active:
            logger.debug(f"Telegram integration disabled for tenant {tenant_id}")
            return False
        
        if not integration.owner_chat_id:
            logger.debug(f"No owner_chat_id configured for tenant {tenant_id}")
            return False
        
        bot_token = self._decrypt_token(integration)
        
        return await self._send_message(
            bot_token,
            integration.owner_chat_id,
            text,
            parse_mode=parse_mode,
        )
    
    # =========================================================================
    # Token Helpers
    # =========================================================================
    
    def _decrypt_token(self, integration: TelegramIntegration) -> str:
        """Decrypt bot token from integration."""
        return self._encryption.decrypt(integration.bot_token_encrypted)
    
    def get_masked_token(self, integration: TelegramIntegration) -> str:
        """Get masked token for display."""
        try:
            token = self._decrypt_token(integration)
            return mask_value(token, visible_chars=8)
        except Exception:
            return "••••••••"
    
    # =========================================================================
    # Telegram API Methods
    # =========================================================================
    
    async def _get_bot_info(self, token: str) -> dict | None:
        """Get bot info from Telegram API (getMe).
        
        Args:
            token: Bot token
            
        Returns:
            Bot info dict or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
                response = await client.get(
                    f"{TELEGRAM_API_URL.format(token=token)}/getMe"
                )
                data = response.json()
                
                if data.get("ok"):
                    return data.get("result")
                else:
                    logger.warning(f"getMe failed: {data.get('description')}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error("Timeout calling Telegram getMe")
            return None
        except Exception as e:
            logger.error(f"Error calling Telegram getMe: {e}")
            return None
    
    async def _set_webhook(
        self,
        token: str,
        url: str,
        secret: str,
    ) -> bool:
        """Set webhook with Telegram API.
        
        Args:
            token: Bot token
            url: Webhook URL
            secret: Secret token for validation
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
                response = await client.post(
                    f"{TELEGRAM_API_URL.format(token=token)}/setWebhook",
                    json={
                        "url": url,
                        "secret_token": secret,
                        "allowed_updates": ["message"],
                    },
                )
                data = response.json()
                
                if data.get("ok"):
                    return True
                else:
                    error = data.get("description", "Unknown error")
                    logger.error(f"setWebhook failed: {error}")
                    raise TelegramWebhookError(error)
                    
        except TelegramWebhookError:
            raise
        except httpx.TimeoutException:
            raise TelegramWebhookError("Connection timeout")
        except Exception as e:
            raise TelegramWebhookError(str(e))
    
    async def _delete_webhook(self, token: str) -> bool:
        """Delete webhook with Telegram API.
        
        Args:
            token: Bot token
            
        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
                response = await client.post(
                    f"{TELEGRAM_API_URL.format(token=token)}/deleteWebhook"
                )
                data = response.json()
                return data.get("ok", False)
                
        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False
    
    async def _send_message(
        self,
        token: str,
        chat_id: int,
        text: str,
        parse_mode: str | None = "HTML",
    ) -> bool:
        """Send message via Telegram API.
        
        Args:
            token: Bot token
            chat_id: Target chat ID
            text: Message text
            parse_mode: HTML or Markdown
            
        Returns:
            True if sent successfully
        """
        # Split long messages
        chunks = self._split_message(text)
        
        try:
            async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
                for chunk in chunks:
                    payload = {
                        "chat_id": chat_id,
                        "text": chunk,
                        "disable_web_page_preview": True,
                    }
                    if parse_mode:
                        payload["parse_mode"] = parse_mode
                    
                    response = await client.post(
                        f"{TELEGRAM_API_URL.format(token=token)}/sendMessage",
                        json=payload,
                    )
                    data = response.json()
                    
                    if not data.get("ok"):
                        error = data.get("description", "Unknown error")
                        logger.warning(f"sendMessage failed: {error}")
                        
                        # Try without parse_mode if it failed
                        if parse_mode:
                            payload.pop("parse_mode")
                            response = await client.post(
                                f"{TELEGRAM_API_URL.format(token=token)}/sendMessage",
                                json=payload,
                            )
                            data = response.json()
                            if not data.get("ok"):
                                return False
                        else:
                            return False
                
                return True
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def _split_message(self, text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
        """Split long message into chunks.
        
        Args:
            text: Message text
            limit: Max characters per message
            
        Returns:
            List of message chunks
        """
        if len(text) <= limit:
            return [text]
        
        chunks = []
        current = ""
        
        for paragraph in text.split("\n\n"):
            if len(current) + len(paragraph) + 2 > limit:
                if current:
                    chunks.append(current.strip())
                    current = ""
                
                # Single paragraph too long
                if len(paragraph) > limit:
                    words = paragraph.split()
                    for word in words:
                        if len(current) + len(word) + 1 > limit:
                            if current:
                                chunks.append(current.strip())
                            current = word + " "
                        else:
                            current += word + " "
                else:
                    current = paragraph + "\n\n"
            else:
                current += paragraph + "\n\n"
        
        if current.strip():
            chunks.append(current.strip())
        
        return chunks or [text[:limit]]

