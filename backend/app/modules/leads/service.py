"""Leads module service layer."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import NotFoundError, VersionConflictError
from app.core.logging import get_logger
from app.modules.leads.models import Inquiry, InquiryForm, InquiryStatus
from app.modules.leads.schemas import (
    InquiryAnalytics,
    InquiryCreatePublic,
    InquiryFormCreate,
    InquiryFormUpdate,
    InquiryUpdate,
)

logger = get_logger(__name__)


class InquiryFormService:
    """Service for managing inquiry forms."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, form_id: UUID, tenant_id: UUID) -> InquiryForm:
        """Get inquiry form by ID."""
        stmt = (
            select(InquiryForm)
            .where(InquiryForm.id == form_id)
            .where(InquiryForm.tenant_id == tenant_id)
            .where(InquiryForm.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        form = result.scalar_one_or_none()

        if not form:
            raise NotFoundError("InquiryForm", form_id)

        return form

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
        stmt = (
            select(InquiryForm)
            .where(InquiryForm.tenant_id == tenant_id)
            .where(InquiryForm.deleted_at.is_(None))
            .order_by(InquiryForm.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

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

        if form.version != data.version:
            raise VersionConflictError("InquiryForm", form.version, data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(form, field, value)

        await self.db.flush()
        await self.db.refresh(form)
        return form

    @transactional
    async def soft_delete(self, form_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an inquiry form."""
        form = await self.get_by_id(form_id, tenant_id)
        form.soft_delete()
        await self.db.flush()


class InquiryService:
    """Service for managing inquiries (leads)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, inquiry_id: UUID, tenant_id: UUID) -> Inquiry:
        """Get inquiry by ID."""
        stmt = (
            select(Inquiry)
            .where(Inquiry.id == inquiry_id)
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
            .options(selectinload(Inquiry.form))
        )
        result = await self.db.execute(stmt)
        inquiry = result.scalar_one_or_none()

        if not inquiry:
            raise NotFoundError("Inquiry", inquiry_id)

        return inquiry

    async def list_inquiries(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        form_id: UUID | None = None,
        assigned_to: UUID | None = None,
        utm_source: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Inquiry], int]:
        """List inquiries with filtering and pagination."""
        base_query = (
            select(Inquiry)
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
        )

        if status:
            base_query = base_query.where(Inquiry.status == status)
        if form_id:
            base_query = base_query.where(Inquiry.form_id == form_id)
        if assigned_to:
            base_query = base_query.where(Inquiry.assigned_to == assigned_to)
        if utm_source:
            base_query = base_query.where(Inquiry.utm_source == utm_source)
        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(
                (Inquiry.name.ilike(search_pattern)) |
                (Inquiry.email.ilike(search_pattern)) |
                (Inquiry.company.ilike(search_pattern)) |
                (Inquiry.phone.ilike(search_pattern))
            )

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.options(selectinload(Inquiry.form))
            .order_by(Inquiry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        inquiries = list(result.scalars().all())

        return inquiries, total

    @transactional
    async def create_from_public(
        self,
        tenant_id: UUID,
        data: InquiryCreatePublic,
        ip_address: str | None = None,
    ) -> Inquiry:
        """Create inquiry from public form submission.

        This is the main entry point for public lead capture.
        """
        # Find form if specified
        form_id = None
        if data.form_slug:
            form_service = InquiryFormService(self.db)
            form = await form_service.get_by_slug(data.form_slug, tenant_id)
            if form:
                form_id = form.id

        # Extract analytics data
        analytics = data.analytics or InquiryAnalytics()

        # Create inquiry
        inquiry = Inquiry(
            tenant_id=tenant_id,
            form_id=form_id,
            status=InquiryStatus.NEW.value,
            # Contact info
            name=data.name,
            email=data.email,
            phone=data.phone,
            company=data.company,
            message=data.message,
            # Service context
            service_id=data.service_id,
            # UTM
            utm_source=analytics.utm_source,
            utm_medium=analytics.utm_medium,
            utm_campaign=analytics.utm_campaign,
            utm_term=analytics.utm_term,
            utm_content=analytics.utm_content,
            # Source
            referrer_url=analytics.referrer_url,
            source_url=analytics.source_url,
            page_path=analytics.page_path,
            page_title=analytics.page_title,
            # Device
            user_agent=analytics.user_agent,
            device_type=analytics.device_type,
            browser=analytics.browser,
            os=analytics.os,
            screen_resolution=analytics.screen_resolution,
            # Location
            ip_address=ip_address,
            # Session
            session_id=analytics.session_id,
            session_page_views=analytics.session_page_views,
            time_on_page=analytics.time_on_page,
            # Custom
            custom_fields=data.custom_fields,
        )

        self.db.add(inquiry)
        await self.db.flush()
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
                inquiry.notification_sent_at = datetime.utcnow()
                await self.db.flush()
                
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
                update_data["status"] = new_status.value
            if new_status == InquiryStatus.CONTACTED and inquiry.status != InquiryStatus.CONTACTED.value:
                inquiry.contacted_at = datetime.utcnow()

        for field, value in update_data.items():
            setattr(inquiry, field, value)

        await self.db.flush()
        await self.db.refresh(inquiry, ["form"])

        return inquiry

    @transactional
    async def mark_notification_sent(self, inquiry_id: UUID, tenant_id: UUID) -> None:
        """Mark inquiry notification as sent."""
        inquiry = await self.get_by_id(inquiry_id, tenant_id)
        inquiry.notification_sent = True
        inquiry.notification_sent_at = datetime.utcnow()
        await self.db.flush()

    @transactional
    async def soft_delete(self, inquiry_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an inquiry."""
        inquiry = await self.get_by_id(inquiry_id, tenant_id)
        inquiry.soft_delete()
        await self.db.flush()

    async def get_analytics_summary(
        self,
        tenant_id: UUID,
        days: int = 30,
    ) -> dict:
        """Get analytics summary for inquiries.

        Returns aggregated stats by status, UTM source, device type, and daily counts.
        """
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=days)

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

