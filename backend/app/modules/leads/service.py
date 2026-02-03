"""Leads module service layer."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.pagination import paginate_query
from app.modules.leads.models import Inquiry, InquiryForm, InquiryStatus
from app.modules.leads.schemas import (
    FORM_SLUG_MVP_BRIEF,
    FORM_SLUG_QUICK,
    InquiryAnalytics,
    InquiryCreatePublic,
    InquiryFormCreate,
    InquiryFormUpdate,
    InquiryUpdate,
)

logger = get_logger(__name__)


class InquiryFormService(BaseService[InquiryForm]):
    """Service for managing inquiry forms."""

    model = InquiryForm

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def get_by_id(self, form_id: UUID, tenant_id: UUID) -> InquiryForm:
        """Get inquiry form by ID."""
        return await self._get_by_id(form_id, tenant_id)

    async def get_by_slug(self, slug: str, tenant_id: UUID) -> InquiryForm | None:
        """Get inquiry form by slug."""
        stmt = (
            select(InquiryForm)
            .where(InquiryForm.slug == slug)
            .where(InquiryForm.tenant_id == tenant_id)
            .where(InquiryForm.deleted_at.is_(None))
            .where(InquiryForm.is_active.is_(True))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_forms(self, tenant_id: UUID) -> list[InquiryForm]:
        """List all inquiry forms."""
        return await self._list_all(
            tenant_id,
            order_by=[InquiryForm.sort_order],
        )

    @transactional
    async def create(self, tenant_id: UUID, data: InquiryFormCreate) -> InquiryForm:
        """Create a new inquiry form."""
        form = InquiryForm(tenant_id=tenant_id, **data.model_dump())
        self.db.add(form)
        await self.db.flush()
        await self.db.refresh(form)
        return form

    @transactional
    async def update(
        self, form_id: UUID, tenant_id: UUID, data: InquiryFormUpdate
    ) -> InquiryForm:
        """Update an inquiry form."""
        form = await self.get_by_id(form_id, tenant_id)
        form.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(form, field, value)

        await self.db.flush()
        await self.db.refresh(form)
        return form

    @transactional
    async def soft_delete(self, form_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an inquiry form."""
        await self._soft_delete(form_id, tenant_id)


class InquiryService(BaseService[Inquiry]):
    """Service for managing inquiries (leads)."""

    model = Inquiry

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    def _get_default_options(self) -> list:
        """Get default eager loading options."""
        return [selectinload(Inquiry.form)]

    async def get_by_id(self, inquiry_id: UUID, tenant_id: UUID) -> Inquiry:
        """Get inquiry by ID."""
        return await self._get_by_id(inquiry_id, tenant_id)

    async def list_inquiries(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        form_id: UUID | None = None,
        form_slug: str | None = None,
        assigned_to: UUID | None = None,
        utm_source: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Inquiry], int]:
        """List inquiries with filtering and pagination."""
        filters = []
        if status:
            filters.append(Inquiry.status == status)
        if form_id:
            filters.append(Inquiry.form_id == form_id)
        if form_slug:
            form_service = InquiryFormService(self.db)
            form = await form_service.get_by_slug(form_slug, tenant_id)
            if form:
                filters.append(Inquiry.form_id == form.id)
        if assigned_to:
            filters.append(Inquiry.assigned_to == assigned_to)
        if utm_source:
            filters.append(Inquiry.utm_source == utm_source)

        base_query = self._build_base_query(tenant_id, filters=filters)

        # Add search filter separately (complex OR condition)
        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(
                (Inquiry.name.ilike(search_pattern)) |
                (Inquiry.email.ilike(search_pattern)) |
                (Inquiry.company.ilike(search_pattern)) |
                (Inquiry.phone.ilike(search_pattern))
            )

        return await paginate_query(
            self.db,
            base_query,
            page,
            page_size,
            options=self._get_default_options(),
            order_by=[Inquiry.created_at.desc()],
        )

    def _build_custom_fields_and_message(
        self, data: InquiryCreatePublic
    ) -> tuple[dict | None, str | None]:
        """Merge brief fields into custom_fields and pick message for inquiry.

        - quick: message from data.message; custom_fields = { telegram?, consent }
        - mvp-brief: message = data.idea; custom_fields = idea, market, audience, ...
        """
        custom = dict(data.custom_fields or {})

        if data.form_slug == FORM_SLUG_QUICK:
            if data.telegram is not None:
                custom["telegram"] = data.telegram
            if data.consent is not None:
                custom["consent"] = data.consent
            return custom if custom else None, data.message

        if data.form_slug == FORM_SLUG_MVP_BRIEF or data.idea is not None:
            brief = {
                "idea": data.idea,
                "market": data.market,
                "audience": data.audience,
                "audienceSize": data.audienceSize,
                "aiRequired": data.aiRequired,
                "appTypes": data.appTypes,
                "integrations": data.integrations,
                "budget": data.budget,
                "urgency": data.urgency,
                "source": data.source,
                "telegram": data.telegram,
                "consent": data.consent,
            }
            brief = {k: v for k, v in brief.items() if v is not None}
            custom.update(brief)
            message = data.idea or data.message
            return custom if custom else None, message

        if data.telegram is not None:
            custom["telegram"] = data.telegram
        if data.consent is not None:
            custom["consent"] = data.consent
        return custom if custom else None, data.message

    @transactional
    async def create_from_public(
        self,
        tenant_id: UUID,
        data: InquiryCreatePublic,
        ip_address: str | None = None,
    ) -> Inquiry:
        """Create inquiry from public form submission.

        This is the main entry point for public lead capture.
        Supports form_slug quick (short form) and mvp-brief (full brief).
        """
        # Find form if specified
        form_id = None
        if data.form_slug:
            form_service = InquiryFormService(self.db)
            form = await form_service.get_by_slug(data.form_slug, tenant_id)
            if form:
                form_id = form.id

        custom_fields, message = self._build_custom_fields_and_message(data)
        analytics = data.analytics or InquiryAnalytics()

        inquiry = Inquiry(
            tenant_id=tenant_id,
            form_id=form_id,
            status=InquiryStatus.NEW.value,
            name=data.name,
            email=data.email,
            phone=data.phone,
            company=data.company,
            message=message,
            service_id=data.service_id,
            utm_source=analytics.utm_source,
            utm_medium=analytics.utm_medium,
            utm_campaign=analytics.utm_campaign,
            utm_term=analytics.utm_term,
            utm_content=analytics.utm_content,
            referrer_url=analytics.referrer_url,
            source_url=analytics.source_url,
            page_path=analytics.page_path,
            page_title=analytics.page_title,
            user_agent=analytics.user_agent,
            device_type=analytics.device_type,
            browser=analytics.browser,
            os=analytics.os,
            screen_resolution=analytics.screen_resolution,
            ip_address=ip_address,
            session_id=analytics.session_id,
            session_page_views=analytics.session_page_views,
            time_on_page=analytics.time_on_page,
            custom_fields=custom_fields,
        )

        self.db.add(inquiry)
        await self.db.flush()
        await self.db.refresh(inquiry)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(inquiry, ["form"])

        logger.info(
            "inquiry_created",
            inquiry_id=str(inquiry.id),
            tenant_id=str(tenant_id),
            form_id=str(form_id) if form_id else None,
            utm_source=analytics.utm_source,
            device_type=analytics.device_type,
        )

        # Send Telegram notification to site owner
        await self._send_telegram_notification(tenant_id, inquiry)

        return inquiry
    
    async def _send_telegram_notification(
        self,
        tenant_id: UUID,
        inquiry: Inquiry,
    ) -> None:
        """Send Telegram notification about new inquiry.
        
        This is a fire-and-forget operation - failures are logged but don't
        affect the inquiry creation.
        """
        try:
            from app.modules.telegram.notifier import TelegramNotifier
            
            notifier = TelegramNotifier(self.db)
            sent = await notifier.send_new_inquiry(tenant_id, inquiry)
            
            if sent:
                inquiry.notification_sent = True
                inquiry.notification_sent_at = datetime.now(UTC)
                await self.db.flush()
                await self.db.refresh(inquiry)  # Refresh to update all attributes including updated_at
                
        except Exception as e:
            logger.warning(
                "telegram_notification_failed",
                inquiry_id=str(inquiry.id),
                tenant_id=str(tenant_id),
                error=str(e),
            )

    @transactional
    async def update(
        self, inquiry_id: UUID, tenant_id: UUID, data: InquiryUpdate
    ) -> Inquiry:
        """Update inquiry (admin)."""
        inquiry = await self.get_by_id(inquiry_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        # Handle status change to contacted
        if "status" in update_data:
            new_status = update_data["status"]
            if isinstance(new_status, InquiryStatus):
                new_status = new_status.value
            update_data["status"] = new_status
            if new_status == InquiryStatus.CONTACTED.value and inquiry.status != InquiryStatus.CONTACTED.value:
                inquiry.contacted_at = datetime.now(UTC)

        for field, value in update_data.items():
            setattr(inquiry, field, value)

        await self.db.flush()
        await self.db.refresh(inquiry)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(inquiry, ["form"])

        return inquiry

    @transactional
    async def mark_notification_sent(self, inquiry_id: UUID, tenant_id: UUID) -> None:
        """Mark inquiry notification as sent."""
        inquiry = await self.get_by_id(inquiry_id, tenant_id)
        inquiry.notification_sent = True
        inquiry.notification_sent_at = datetime.now(UTC)
        await self.db.flush()

    @transactional
    async def soft_delete(self, inquiry_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an inquiry."""
        await self._soft_delete(inquiry_id, tenant_id)

    async def get_analytics_summary(
        self,
        tenant_id: UUID,
        days: int = 30,
    ) -> dict:
        """Get analytics summary for inquiries.

        Returns aggregated stats by status, UTM source, device type, and daily counts.
        """
        from datetime import timedelta

        start_date = datetime.now(UTC) - timedelta(days=days)

        # Base query for period
        base_query = (
            select(Inquiry)
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.created_at >= start_date)
        )

        # Total count
        total_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(total_stmt)).scalar() or 0

        # By status
        status_stmt = (
            select(Inquiry.status, func.count())
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.created_at >= start_date)
            .group_by(Inquiry.status)
        )
        status_result = await self.db.execute(status_stmt)
        by_status = {row[0]: row[1] for row in status_result}

        # By UTM source
        utm_stmt = (
            select(Inquiry.utm_source, func.count())
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.created_at >= start_date)
            .where(Inquiry.utm_source.isnot(None))
            .group_by(Inquiry.utm_source)
        )
        utm_result = await self.db.execute(utm_stmt)
        by_utm_source = {row[0]: row[1] for row in utm_result}

        # By device type
        device_stmt = (
            select(Inquiry.device_type, func.count())
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.created_at >= start_date)
            .where(Inquiry.device_type.isnot(None))
            .group_by(Inquiry.device_type)
        )
        device_result = await self.db.execute(device_stmt)
        by_device_type = {row[0]: row[1] for row in device_result}

        return {
            "total": total,
            "by_status": by_status,
            "by_utm_source": by_utm_source,
            "by_device_type": by_device_type,
        }

