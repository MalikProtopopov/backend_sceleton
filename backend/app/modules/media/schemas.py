"""Pydantic schemas for assets module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FileAssetBase(BaseModel):
    """Base schema for file asset."""

    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    s3_bucket: str
    s3_key: str
    s3_url: str
    cdn_url: str | None = None
    width: int | None = None
    height: int | None = None
    alt_text: str | None = None
    folder: str | None = None


class FileAssetCreate(BaseModel):
    """Schema for creating file asset (internal use)."""

    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    s3_bucket: str
    s3_key: str
    s3_url: str
    cdn_url: str | None = None
    width: int | None = None
    height: int | None = None
    alt_text: str | None = None
    folder: str | None = None
    uploaded_by: UUID | None = None


class FileAssetUpdate(BaseModel):
    """Schema for updating file asset."""

    alt_text: str | None = Field(default=None, max_length=500)
    folder: str | None = Field(default=None, max_length=100)


class FileAssetResponse(FileAssetBase):
    """Schema for file asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    url: str
    is_image: bool
    uploaded_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class FileAssetListResponse(BaseModel):
    """Schema for file asset list response."""

    items: list[FileAssetResponse]
    total: int
    page: int
    page_size: int


class UploadURLRequest(BaseModel):
    """Request for presigned upload URL."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., max_length=100)
    folder: str | None = Field(default=None, max_length=100)


class UploadURLResponse(BaseModel):
    """Response with presigned upload URL."""

    upload_url: str
    file_url: str
    s3_key: str
    expires_in: int = 3600

