"""Pydantic schemas for audit module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditUserResponse(BaseModel):
    """User info in audit log."""

    id: UUID | None = None
    email: str | None = None
    name: str | None = None


class AuditResourceResponse(BaseModel):
    """Resource info in audit log."""

    type: str
    id: UUID | None = None
    name: str | None = None


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: UUID | None = None
    resource_name: str | None = None
    user: AuditUserResponse | None = None
    changes: dict | None = None
    ip_address: str | None = None
    status: str


class AuditLogListResponse(BaseModel):
    """Schema for audit log list response."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditLogCreate(BaseModel):
    """Schema for creating an audit log entry."""

    action: str
    resource_type: str
    resource_id: UUID | None = None
    resource_name: str | None = None
    changes: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status: str = "success"
    error_message: str | None = None

