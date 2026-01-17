"""Export module service layer."""

import csv
import io
import json
from datetime import datetime
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
            default_columns = ["name", "email", "phone", "company", "status", "utm_source", "created_at"]
        elif resource_type == ExportResourceType.EMPLOYEES:
            data = await self._get_employees(tenant_id)
            default_columns = ["name", "position", "email", "phone", "is_published"]
        elif resource_type == ExportResourceType.SEO_ROUTES:
            data = await self._get_seo_routes(tenant_id)
            default_columns = ["path", "locale", "meta_title", "meta_description", "created_at"]
        elif resource_type == ExportResourceType.AUDIT_LOGS:
            data = await self._get_audit_logs(tenant_id, date_from, date_to)
            default_columns = ["timestamp", "user_email", "action", "resource_type", "resource_name"]
        else:
            data = []
            default_columns = []

        # Use specified columns or defaults
        use_columns = columns if columns else default_columns

        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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
                "name": i.name,
                "email": i.email or "",
                "phone": i.phone or "",
                "company": i.company or "",
                "message": i.message or "",
                "status": i.status,
                "utm_source": i.utm_source or "",
                "utm_medium": i.utm_medium or "",
                "utm_campaign": i.utm_campaign or "",
                "device_type": i.device_type or "",
                "source_url": i.source_url or "",
                "created_at": i.created_at.isoformat() if i.created_at else "",
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
            .where(SEORoute.deleted_at.is_(None))
            .order_by(SEORoute.path)
        )

        result = await self.db.execute(stmt)
        routes = result.scalars().all()

        return [
            {
                "path": r.path,
                "locale": r.locale,
                "meta_title": r.meta_title or "",
                "meta_description": r.meta_description or "",
                "canonical_url": r.canonical_url or "",
                "robots_index": "Yes" if r.robots_index else "No",
                "robots_follow": "Yes" if r.robots_follow else "No",
                "created_at": r.created_at.isoformat() if r.created_at else "",
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

