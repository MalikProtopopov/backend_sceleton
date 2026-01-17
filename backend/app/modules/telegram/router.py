"""Telegram integration API router.

Provides endpoints for managing Telegram bot integration
and receiving webhook callbacks from Telegram.
"""

import hmac
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import InvalidWebhookSecretError
from app.core.security import CurrentUser, get_current_tenant_id, get_current_active_user
from app.modules.telegram.exceptions import (
    TelegramIntegrationNotFoundError,
    TelegramNotConfiguredError,
)
from app.modules.telegram.schemas import (
    BotInfoResponse,
    SendTestMessageRequest,
    SetWebhookRequest,
    TelegramIntegrationCreate,
    TelegramIntegrationResponse,
    TelegramIntegrationUpdate,
    TestMessageResponse,
    WebhookStatusResponse,
    WebhookUrlResponse,
)
from app.modules.telegram.service import TelegramIntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram")


def get_telegram_service(db: AsyncSession = Depends(get_db)) -> TelegramIntegrationService:
    """Dependency for Telegram service."""
    return TelegramIntegrationService(db)


# =============================================================================
# Integration Management Endpoints
# =============================================================================


@router.get(
    "/integration",
    response_model=TelegramIntegrationResponse | None,
    summary="Get Telegram integration",
    description="Get current Telegram integration settings for the tenant.",
)
async def get_integration(
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> TelegramIntegrationResponse | None:
    """Get Telegram integration settings."""
    integration = await service.get_integration(tenant_id)
    
    if not integration:
        return None
    
    # Build response with masked token
    response = TelegramIntegrationResponse.model_validate(integration)
    response.bot_token_masked = service.get_masked_token(integration)
    
    return response


@router.post(
    "/integration",
    response_model=TelegramIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create/update Telegram integration",
    description="""
Create or update Telegram bot integration.

**Process:**
1. Validates bot token with Telegram API (getMe)
2. Stores encrypted token
3. Generates webhook secret

**How to get bot token:**
1. Open @BotFather in Telegram
2. Send /newbot command
3. Follow instructions
4. Copy the token
    """,
)
async def create_integration(
    data: TelegramIntegrationCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> TelegramIntegrationResponse:
    """Create or update Telegram integration."""
    integration = await service.create_integration(tenant_id, data)
    
    response = TelegramIntegrationResponse.model_validate(integration)
    response.bot_token_masked = service.get_masked_token(integration)
    
    return response


@router.patch(
    "/integration",
    response_model=TelegramIntegrationResponse,
    summary="Update Telegram integration",
    description="Update existing Telegram integration settings.",
)
async def update_integration(
    data: TelegramIntegrationUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> TelegramIntegrationResponse:
    """Update Telegram integration."""
    integration = await service.update_integration(tenant_id, data)
    
    response = TelegramIntegrationResponse.model_validate(integration)
    response.bot_token_masked = service.get_masked_token(integration)
    
    return response


@router.delete(
    "/integration",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Telegram integration",
    description="Delete Telegram integration and remove webhook.",
)
async def delete_integration(
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> None:
    """Delete Telegram integration."""
    await service.delete_integration(tenant_id)


# =============================================================================
# Webhook Management Endpoints
# =============================================================================


@router.get(
    "/integration/webhook-url",
    response_model=WebhookUrlResponse,
    summary="Get webhook URL",
    description="Get the webhook URL to configure with Telegram.",
)
async def get_webhook_url(
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> WebhookUrlResponse:
    """Get webhook URL for configuration."""
    integration = await service.get_integration_or_raise(tenant_id)
    
    if not settings.public_api_url:
        return WebhookUrlResponse(
            webhook_url="",
            is_configured=False,
            message=(
                "PUBLIC_API_URL not configured. "
                "Set PUBLIC_API_URL environment variable to your domain "
                "(e.g., https://yourdomain.com)"
            ),
        )
    
    webhook_url = service.get_webhook_url(integration)
    
    return WebhookUrlResponse(
        webhook_url=webhook_url or "",
        is_configured=True,
        message=None,
    )


@router.post(
    "/integration/webhook",
    response_model=WebhookStatusResponse,
    summary="Set webhook",
    description="""
Register webhook URL with Telegram.

**Requirements:**
- URL must be HTTPS
- URL must be publicly accessible
- For local development, use ngrok or similar
    """,
)
async def set_webhook(
    data: SetWebhookRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> WebhookStatusResponse:
    """Set Telegram webhook."""
    success = await service.set_webhook(tenant_id, data.webhook_url)
    
    return WebhookStatusResponse(
        success=success,
        message="Webhook registered successfully" if success else "Failed to register webhook",
    )


@router.delete(
    "/integration/webhook",
    response_model=WebhookStatusResponse,
    summary="Remove webhook",
    description="Remove webhook from Telegram.",
)
async def remove_webhook(
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> WebhookStatusResponse:
    """Remove Telegram webhook."""
    success = await service.remove_webhook(tenant_id)
    
    return WebhookStatusResponse(
        success=success,
        message="Webhook removed" if success else "Failed to remove webhook",
    )


# =============================================================================
# Test Message Endpoint
# =============================================================================


@router.post(
    "/integration/test",
    response_model=TestMessageResponse,
    summary="Send test message",
    description="Send a test message to verify configuration.",
)
async def send_test_message(
    data: SendTestMessageRequest | None = None,
    tenant_id: UUID = Depends(get_current_tenant_id),
    current_user: CurrentUser = Depends(get_current_active_user),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> TestMessageResponse:
    """Send test message."""
    chat_id = data.chat_id if data else None
    
    try:
        integration = await service.get_integration_or_raise(tenant_id)
        target_chat_id = chat_id or integration.owner_chat_id
        
        if not target_chat_id:
            return TestMessageResponse(
                success=False,
                message="No chat_id provided and owner_chat_id not configured",
            )
        
        success = await service.send_test_message(tenant_id, chat_id)
        
        return TestMessageResponse(
            success=success,
            message="Test message sent!" if success else "Failed to send message",
            chat_id=target_chat_id,
        )
    except TelegramNotConfiguredError as e:
        return TestMessageResponse(
            success=False,
            message=str(e),
        )


# =============================================================================
# Webhook Handler Endpoint (Public)
# =============================================================================


@router.post(
    "/webhook/{webhook_secret}",
    include_in_schema=False,
    summary="Telegram webhook handler",
)
async def handle_webhook(
    webhook_secret: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
    service: TelegramIntegrationService = Depends(get_telegram_service),
) -> dict:
    """Handle incoming Telegram webhook.
    
    This endpoint is called by Telegram when messages are received.
    Currently only used for validation; notifications are sent outbound.
    """
    # Validate secret token from header
    if not x_telegram_bot_api_secret_token:
        logger.warning("Webhook request without secret token")
        raise InvalidWebhookSecretError("Missing secret token")
    
    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(x_telegram_bot_api_secret_token, webhook_secret):
        logger.warning("Webhook request with invalid secret token")
        raise InvalidWebhookSecretError("Invalid secret token")
    
    # Find integration
    integration = await service.get_integration_by_secret(webhook_secret)
    if not integration or not integration.is_active:
        logger.warning(f"Webhook for unknown/inactive integration: {webhook_secret[:8]}...")
        return {"ok": True}  # Return 200 to prevent Telegram retries
    
    # Parse payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return {"ok": True}
    
    # Log received message (for debugging)
    message = payload.get("message", {})
    if message:
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")[:50]
        logger.info(
            f"Received Telegram message for tenant {integration.tenant_id}: "
            f"chat_id={chat_id}, text={text}..."
        )
    
    # For now, just acknowledge - we only use outbound notifications
    # Future: could handle commands like /start to get chat_id
    
    return {"ok": True}

