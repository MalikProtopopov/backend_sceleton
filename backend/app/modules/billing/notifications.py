"""Billing-related notifications: upgrade requests, limit warnings."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


async def notify_upgrade_request_created(db: AsyncSession, tenant_id: UUID, request_type: str) -> None:
    """Notify platform owner about a new upgrade request."""
    try:
        from app.modules.notifications.service import EmailService
        from app.modules.tenants.models import Tenant
        from sqlalchemy import select

        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await db.execute(stmt)
        tenant = result.scalar_one_or_none()
        tenant_name = tenant.name if tenant else str(tenant_id)

        email_svc = EmailService(db=db)

        from app.config import settings
        admin_email = getattr(settings, "platform_admin_email", None)
        if admin_email:
            await email_svc._send(
                to_email=admin_email,
                subject=f"Новая заявка на апгрейд от {tenant_name}",
                body=(
                    f"Тенант: {tenant_name}\n"
                    f"Тип заявки: {request_type}\n\n"
                    f"Проверьте заявку в панели платформы."
                ),
                email_type="upgrade_request",
                tenant_id=None,
            )

        logger.info("upgrade_request_notification_sent", tenant_id=str(tenant_id), type=request_type)
    except Exception:
        logger.warning("upgrade_request_notification_failed", tenant_id=str(tenant_id))


async def notify_upgrade_request_reviewed(
    db: AsyncSession,
    tenant_id: UUID,
    status: str,
    request_type: str,
) -> None:
    """Notify tenant owner about upgrade request approval or rejection."""
    try:
        from app.modules.notifications.service import EmailService
        from app.modules.tenants.models import Tenant, TenantSettings
        from sqlalchemy import select

        stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        result = await db.execute(stmt)
        ts = result.scalar_one_or_none()
        notify_email = ts.inquiry_email if ts else None

        if not notify_email:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()
            notify_email = tenant.contact_email if tenant else None

        if not notify_email:
            return

        status_text = "одобрена" if status == "approved" else "отклонена"
        email_svc = EmailService(db=db)
        await email_svc._send(
            to_email=notify_email,
            subject=f"Заявка {status_text}",
            body=(
                f"Ваша заявка на {request_type} была {status_text}.\n\n"
                f"Подробности доступны в панели администратора."
            ),
            email_type="upgrade_review",
            tenant_id=tenant_id,
        )

        logger.info("upgrade_review_notification_sent", tenant_id=str(tenant_id), status=status)
    except Exception:
        logger.warning("upgrade_review_notification_failed", tenant_id=str(tenant_id))


async def notify_limit_warning(
    db: AsyncSession,
    tenant_id: UUID,
    resource: str,
    current: int,
    limit: int,
) -> None:
    """Notify tenant owner when approaching resource limit (80%+)."""
    try:
        from app.modules.notifications.service import EmailService
        from app.modules.tenants.models import TenantSettings
        from sqlalchemy import select

        stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        result = await db.execute(stmt)
        ts = result.scalar_one_or_none()
        notify_email = ts.inquiry_email if ts else None

        if not notify_email:
            return

        pct = round(current / limit * 100) if limit > 0 else 100
        email_svc = EmailService(db=db)
        await email_svc._send(
            to_email=notify_email,
            subject=f"Приближение к лимиту: {resource}",
            body=(
                f"Использование ресурса '{resource}': {current} из {limit} ({pct}%).\n\n"
                f"Рекомендуем обновить тарифный план для увеличения лимитов."
            ),
            email_type="limit_warning",
            tenant_id=tenant_id,
        )

        logger.info(
            "limit_warning_sent",
            tenant_id=str(tenant_id),
            resource=resource,
            current=current,
            limit=limit,
        )
    except Exception:
        logger.warning("limit_warning_notification_failed", tenant_id=str(tenant_id), resource=resource)


async def notify_limit_exceeded(
    db: AsyncSession,
    tenant_id: UUID,
    resource: str,
    current: int,
    limit: int,
) -> None:
    """Notify tenant owner when resource limit is exceeded (100%)."""
    try:
        from app.modules.notifications.service import EmailService
        from app.modules.tenants.models import TenantSettings, Tenant
        from sqlalchemy import select

        stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        result = await db.execute(stmt)
        ts = result.scalar_one_or_none()
        notify_email = ts.inquiry_email if ts else None

        if not notify_email:
            stmt = select(Tenant).where(Tenant.id == tenant_id)
            result = await db.execute(stmt)
            tenant = result.scalar_one_or_none()
            notify_email = tenant.contact_email if tenant else None

        if not notify_email:
            return

        email_svc = EmailService(db=db)
        await email_svc._send(
            to_email=notify_email,
            subject=f"Лимит достигнут: {resource}",
            body=(
                f"Лимит ресурса '{resource}' исчерпан: {current} из {limit}.\n\n"
                f"Создание новых записей заблокировано.\n"
                f"Обновите тарифный план или свяжитесь с поддержкой."
            ),
            email_type="limit_exceeded",
            tenant_id=tenant_id,
        )

        logger.info(
            "limit_exceeded_sent",
            tenant_id=str(tenant_id),
            resource=resource,
        )
    except Exception:
        logger.warning("limit_exceeded_notification_failed", tenant_id=str(tenant_id), resource=resource)
