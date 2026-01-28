"""Export module service layer."""

import csv
import io
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.models import AuditLog
from app.modules.company.models import Employee, EmployeeLocale
from app.modules.export.schemas import ExportFormat, ExportResourceType
from app.modules.leads.models import Inquiry
from app.modules.seo.models import SEORoute


class ExportService:
    """Service for exporting data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def export_data(
        self,
        tenant_id: UUID,
        resource_type: ExportResourceType,
        format: ExportFormat,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        columns: list[str] | None = None,
    ) -> tuple[str, str, str]:
        """Export data to specified format.

        Returns tuple of (content, content_type, filename).
        """
        # Get data based on resource type
        if resource_type == ExportResourceType.INQUIRIES:
            data = await self._get_inquiries(tenant_id, status, date_from, date_to)
            default_columns = [
                "id", "name", "email", "phone", "company", "message",
                "status", "form_id", "service_id", "assigned_to", "notes",
                "contacted_at", "notification_sent", "notification_sent_at",
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                "referrer_url", "source_url", "page_path", "page_title",
                "user_agent", "device_type", "browser", "os", "screen_resolution",
                "ip_address", "country", "city", "region",
                "session_id", "session_page_views", "time_on_page",
                "custom_fields", "created_at", "updated_at",
            ]
        elif resource_type == ExportResourceType.EMPLOYEES:
            data = await self._get_employees(tenant_id)
            default_columns = ["name", "position", "email", "phone", "is_published", "linkedin_url", "telegram_url"]
        elif resource_type == ExportResourceType.SEO_ROUTES:
            data = await self._get_seo_routes(tenant_id)
            default_columns = [
                "id", "path", "locale", "title",
                "meta_title", "meta_description", "meta_keywords", "og_image",
                "canonical_url", "robots_index", "robots_follow",
                "structured_data", "sitemap_priority", "sitemap_changefreq", "include_in_sitemap",
                "version", "created_at", "updated_at",
            ]
        elif resource_type == ExportResourceType.AUDIT_LOGS:
            data = await self._get_audit_logs(tenant_id, date_from, date_to)
            default_columns = [
                "timestamp", "user_email", "user_name", "action",
                "resource_type", "resource_id", "resource_name", "ip_address", "status",
            ]
        else:
            data = []
            default_columns = []

        # Use specified columns or defaults
        use_columns = columns if columns else default_columns

        # Generate filename
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{resource_type.value}_{timestamp}.{format.value}"

        # Format output
        if format == ExportFormat.CSV:
            content = self._to_csv(data, use_columns)
            content_type = "text/csv"
        else:
            content = self._to_json(data, use_columns)
            content_type = "application/json"

        return content, content_type, filename

    async def _get_inquiries(
        self,
        tenant_id: UUID,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get inquiries for export."""
        stmt = (
            select(Inquiry)
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
            .order_by(Inquiry.created_at.desc())
        )

        if status:
            stmt = stmt.where(Inquiry.status == status)

        if date_from:
            stmt = stmt.where(Inquiry.created_at >= datetime.fromisoformat(date_from))

        if date_to:
            stmt = stmt.where(Inquiry.created_at <= datetime.fromisoformat(date_to))

        result = await self.db.execute(stmt)
        inquiries = result.scalars().all()

        return [
            {
                # ID
                "id": str(i.id),
                # Contact Info
                "name": i.name,
                "email": i.email or "",
                "phone": i.phone or "",
                "company": i.company or "",
                "message": i.message or "",
                # Status & Processing
                "status": i.status,
                "form_id": str(i.form_id) if i.form_id else "",
                "service_id": str(i.service_id) if i.service_id else "",
                "assigned_to": str(i.assigned_to) if i.assigned_to else "",
                "notes": i.notes or "",
                "contacted_at": i.contacted_at.isoformat() if i.contacted_at else "",
                "notification_sent": "Yes" if i.notification_sent else "No",
                "notification_sent_at": i.notification_sent_at.isoformat() if i.notification_sent_at else "",
                # UTM Tracking
                "utm_source": i.utm_source or "",
                "utm_medium": i.utm_medium or "",
                "utm_campaign": i.utm_campaign or "",
                "utm_term": i.utm_term or "",
                "utm_content": i.utm_content or "",
                "referrer_url": i.referrer_url or "",
                # Page Context
                "source_url": i.source_url or "",
                "page_path": i.page_path or "",
                "page_title": i.page_title or "",
                # Device & Browser
                "user_agent": i.user_agent or "",
                "device_type": i.device_type or "",
                "browser": i.browser or "",
                "os": i.os or "",
                "screen_resolution": i.screen_resolution or "",
                # Location
                "ip_address": i.ip_address or "",
                "country": i.country or "",
                "city": i.city or "",
                "region": i.region or "",
                # Session Info
                "session_id": i.session_id or "",
                "session_page_views": str(i.session_page_views) if i.session_page_views is not None else "",
                "time_on_page": str(i.time_on_page) if i.time_on_page is not None else "",
                # Custom Fields
                "custom_fields": json.dumps(i.custom_fields, ensure_ascii=False) if i.custom_fields else "",
                # Timestamps
                "created_at": i.created_at.isoformat() if i.created_at else "",
                "updated_at": i.updated_at.isoformat() if i.updated_at else "",
            }
            for i in inquiries
        ]

    async def _get_employees(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Get employees for export."""
        stmt = (
            select(Employee)
            .where(Employee.tenant_id == tenant_id)
            .where(Employee.deleted_at.is_(None))
            .options(selectinload(Employee.locales))
            .order_by(Employee.sort_order)
        )

        result = await self.db.execute(stmt)
        employees = result.scalars().all()

        data = []
        for emp in employees:
            # Get first locale
            locale = emp.locales[0] if emp.locales else None
            data.append({
                "name": f"{locale.first_name} {locale.last_name}" if locale else "",
                "position": locale.position if locale else "",
                "email": emp.email or "",
                "phone": emp.phone or "",
                "is_published": "Yes" if emp.is_published else "No",
                "linkedin_url": emp.linkedin_url or "",
                "telegram_url": emp.telegram_url or "",
            })

        return data

    async def _get_seo_routes(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Get SEO routes for export."""
        stmt = (
            select(SEORoute)
            .where(SEORoute.tenant_id == tenant_id)
            .order_by(SEORoute.path)
        )

        result = await self.db.execute(stmt)
        routes = result.scalars().all()

        return [
            {
                # ID
                "id": str(r.id),
                # Route Info
                "path": r.path,
                "locale": r.locale,
                "title": r.title or "",
                # SEO Meta Tags
                "meta_title": r.meta_title or "",
                "meta_description": r.meta_description or "",
                "meta_keywords": r.meta_keywords or "",
                # Open Graph
                "og_image": r.og_image or "",
                # Canonical & Robots
                "canonical_url": r.canonical_url or "",
                "robots_index": "Yes" if r.robots_index else "No",
                "robots_follow": "Yes" if r.robots_follow else "No",
                # Structured Data
                "structured_data": r.structured_data or "",
                # Sitemap
                "sitemap_priority": str(r.sitemap_priority) if r.sitemap_priority is not None else "",
                "sitemap_changefreq": r.sitemap_changefreq or "",
                "include_in_sitemap": "Yes" if r.include_in_sitemap else "No",
                # Version & Timestamps
                "version": str(r.version),
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "updated_at": r.updated_at.isoformat() if r.updated_at else "",
            }
            for r in routes
        ]

    async def _get_audit_logs(
        self,
        tenant_id: UUID,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get audit logs for export."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(AuditLog.timestamp.desc())
        )

        if date_from:
            stmt = stmt.where(AuditLog.timestamp >= datetime.fromisoformat(date_from))

        if date_to:
            stmt = stmt.where(AuditLog.timestamp <= datetime.fromisoformat(date_to))

        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "timestamp": log.timestamp.isoformat() if log.timestamp else "",
                "user_email": log.user_email or "",
                "user_name": log.user_name or "",
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": str(log.resource_id) if log.resource_id else "",
                "resource_name": log.resource_name or "",
                "ip_address": log.ip_address or "",
                "status": log.status,
            }
            for log in logs
        ]

    def _to_csv(self, data: list[dict[str, Any]], columns: list[str]) -> str:
        """Convert data to CSV format."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        return output.getvalue()

    def _to_json(self, data: list[dict[str, Any]], columns: list[str]) -> str:
        """Convert data to JSON format."""
        # Filter to only include specified columns
        filtered_data = [
            {k: v for k, v in row.items() if k in columns}
            for row in data
        ]
        return json.dumps(filtered_data, indent=2, ensure_ascii=False)

