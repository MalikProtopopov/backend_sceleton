"""Telegram integration Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Request Schemas
# =============================================================================


class TelegramIntegrationCreate(BaseModel):
    """Schema for creating Telegram integration."""
    
    bot_token: str = Field(
        ...,
        min_length=20,
        max_length=255,
        description="Telegram bot token from @BotFather",
    )
    owner_chat_id: int | None = Field(
        default=None,
        description="Chat ID of owner for receiving notifications",
    )
    welcome_message: str | None = Field(
        default=None,
        max_length=4096,
        description="Custom welcome message for /start command",
    )


class TelegramIntegrationUpdate(BaseModel):
    """Schema for updating Telegram integration."""
    
    bot_token: str | None = Field(
        default=None,
        min_length=20,
        max_length=255,
        description="New bot token (will re-validate with Telegram)",
    )
    owner_chat_id: int | None = Field(
        default=None,
        description="New chat ID for notifications",
    )
    is_active: bool | None = Field(
        default=None,
        description="Enable/disable integration",
    )
    welcome_message: str | None = Field(
        default=None,
        max_length=4096,
        description="Custom welcome message",
    )


class SetWebhookRequest(BaseModel):
    """Schema for setting webhook."""
    
    webhook_url: str = Field(
        ...,
        min_length=10,
        max_length=512,
        description="HTTPS URL for webhook",
    )


class SendTestMessageRequest(BaseModel):
    """Schema for sending test message."""
    
    chat_id: int | None = Field(
        default=None,
        description="Override chat ID for test (uses owner_chat_id if not provided)",
    )


# =============================================================================
# Response Schemas
# =============================================================================


class TelegramIntegrationResponse(BaseModel):
    """Schema for Telegram integration response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    bot_username: str | None
    owner_chat_id: int | None
    webhook_url: str | None
    is_webhook_active: bool
    is_active: bool
    welcome_message: str | None
    created_at: datetime
    updated_at: datetime
    
    # Masked token for display
    bot_token_masked: str | None = None


class WebhookUrlResponse(BaseModel):
    """Schema for webhook URL response."""
    
    webhook_url: str = Field(
        description="Full webhook URL to use with Telegram",
    )
    is_configured: bool = Field(
        description="Whether PUBLIC_API_URL is properly configured",
    )
    message: str | None = Field(
        default=None,
        description="Info/error message",
    )


class WebhookStatusResponse(BaseModel):
    """Schema for webhook operation result."""
    
    success: bool
    message: str | None = None


class TestMessageResponse(BaseModel):
    """Schema for test message result."""
    
    success: bool
    message: str | None = None
    chat_id: int | None = None


class BotInfoResponse(BaseModel):
    """Schema for Telegram bot info."""
    
    id: int
    username: str
    first_name: str
    can_join_groups: bool = False
    can_read_all_group_messages: bool = False
    supports_inline_queries: bool = False

