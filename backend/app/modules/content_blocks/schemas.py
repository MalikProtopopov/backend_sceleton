"""Content block Pydantic schemas."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContentBlockType(str, Enum):
    """Type of content block."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    GALLERY = "gallery"
    LINK = "link"
    RESULT = "result"


class DeviceType(str, Enum):
    """Device type for responsive content."""

    MOBILE = "mobile"
    DESKTOP = "desktop"
    BOTH = "both"


class ContentBlockCreate(BaseModel):
    """Schema for creating a content block."""

    locale: str = Field(..., min_length=2, max_length=5)
    block_type: ContentBlockType
    sort_order: int = Field(default=0, description="Display order")
    title: str | None = Field(default=None, max_length=255, description="Block title/heading")
    content: str | None = Field(default=None, description="HTML content for text blocks")
    media_url: str | None = Field(default=None, max_length=500, description="URL for image or video")
    thumbnail_url: str | None = Field(default=None, max_length=500, description="Thumbnail URL for video")
    link_url: str | None = Field(default=None, max_length=500, description="Link URL")
    link_label: str | None = Field(default=None, max_length=255, description="Link button text")
    device_type: DeviceType = Field(default=DeviceType.BOTH, description="Device type: mobile, desktop, both")
    block_metadata: dict | None = Field(default=None, description="Additional metadata (alt, caption, images[], provider, icon)")


class ContentBlockUpdate(BaseModel):
    """Schema for updating a content block."""

    locale: str | None = Field(default=None, min_length=2, max_length=5)
    block_type: ContentBlockType | None = None
    sort_order: int | None = None
    title: str | None = Field(default=None, max_length=255)
    content: str | None = None
    media_url: str | None = Field(default=None, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    link_url: str | None = Field(default=None, max_length=500)
    link_label: str | None = Field(default=None, max_length=255)
    device_type: DeviceType | None = None
    block_metadata: dict | None = None


class ContentBlockResponse(BaseModel):
    """Schema for content block response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    locale: str
    block_type: str
    sort_order: int
    title: str | None = None
    content: str | None = None
    media_url: str | None = None
    thumbnail_url: str | None = None
    link_url: str | None = None
    link_label: str | None = None
    device_type: str | None = None
    block_metadata: dict | None = None


class ContentBlockReorderRequest(BaseModel):
    """Schema for reordering content blocks."""

    locale: str = Field(..., min_length=2, max_length=5)
    block_ids: list[UUID] = Field(..., description="Ordered list of block IDs")
