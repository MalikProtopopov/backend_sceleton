"""Pydantic schemas for export module."""

from enum import Enum

from pydantic import BaseModel, Field


class ExportResourceType(str, Enum):
    """Resource types available for export."""

    INQUIRIES = "inquiries"
    EMPLOYEES = "team"
    SEO_ROUTES = "seo_routes"
    AUDIT_LOGS = "audit_logs"


class ExportFormat(str, Enum):
    """Export file formats."""

    CSV = "csv"
    JSON = "json"


class ExportFilters(BaseModel):
    """Filters for export."""

    status: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class ExportRequest(BaseModel):
    """Schema for export request (for POST method alternative)."""

    resource_type: ExportResourceType
    format: ExportFormat = ExportFormat.CSV
    filters: ExportFilters | None = None
    columns: list[str] | None = None

