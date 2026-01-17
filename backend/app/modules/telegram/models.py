"""Telegram integration database models."""

from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class TelegramIntegration(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Telegram bot integration for a tenant.
    
    Each tenant can have one Telegram bot integration for receiving
    notifications about inquiries, contact forms, etc.
    
    The bot_token is stored encrypted for security.
    """
    
    __tablename__ = "telegram_integrations"
    
    # Bot configuration
    bot_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted Telegram bot token",
    )
    bot_username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Bot username without @ (e.g., 'my_bot')",
    )
    
    # Owner notification settings
    owner_chat_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Chat ID of the owner for receiving notifications",
    )
    
    # Webhook configuration
    webhook_secret: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Secret token for webhook validation",
    )
    webhook_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Current webhook URL",
    )
    is_webhook_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether webhook is currently active",
    )
    
    # Integration status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether integration is enabled",
    )
    
    # Welcome message for /start command (optional)
    welcome_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Custom welcome message for /start command",
    )
    
    __table_args__ = (
        # Each tenant can have only one integration
        Index(
            "ix_telegram_integrations_tenant_unique",
            "tenant_id",
            unique=True,
        ),
        # For webhook lookup
        Index(
            "ix_telegram_integrations_webhook_secret",
            "webhook_secret",
        ),
    )
    
    def __repr__(self) -> str:
        return f"<TelegramIntegration tenant_id={self.tenant_id} bot={self.bot_username}>"

