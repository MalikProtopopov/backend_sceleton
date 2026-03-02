"""Content block database models."""

from enum import Enum
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import Base, SortOrderMixin, TenantMixin, TimestampMixin, UUIDMixin


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


class EntityType(str, Enum):
    """Entity type for content blocks."""

    ARTICLE = "article"
    CASE = "case"
    SERVICE = "service"


class ContentBlock(Base, UUIDMixin, TimestampMixin, TenantMixin, SortOrderMixin):
    """Flexible content block for articles, cases, and services.

    Allows creating structured content with different block types:
    - text: HTML content
    - image: Single image with alt text and caption
    - video: Embedded video (YouTube, RuTube, etc.)
    - gallery: Image slider/gallery
    - link: Link to external resource (website, TG bot, etc.)
    - result: Result block with video, link, and text (for cases)

    Each block can be localized and sorted independently.
    """

    __tablename__ = "content_blocks"

    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Entity type: article, case, service",
    )
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment="ID of the related entity",
    )
    locale: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        comment="Locale code: ru, en, etc.",
    )

    block_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Block type: text, image, video, gallery, link, result",
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional block title/heading",
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="HTML content for text blocks",
    )
    media_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL for image or video",
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Thumbnail URL for video blocks",
    )
    link_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Link URL for link/result blocks",
    )
    link_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Link button text",
    )
    device_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        default=DeviceType.BOTH.value,
        comment="Device type: mobile, desktop, both",
    )
    block_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional metadata (alt, caption, images[], provider, icon)",
    )

    __table_args__ = (
        Index("ix_content_blocks_tenant", "tenant_id"),
        Index("ix_content_blocks_entity", "entity_type", "entity_id", "locale"),
        Index(
            "ix_content_blocks_entity_sorted",
            "entity_type",
            "entity_id",
            "locale",
            "sort_order",
        ),
        CheckConstraint(
            "entity_type IN ('article', 'case', 'service', 'employee', 'product')",
            name="ck_content_blocks_entity_type",
        ),
        CheckConstraint(
            "block_type IN ('text', 'image', 'video', 'gallery', 'link', 'result')",
            name="ck_content_blocks_block_type",
        ),
        CheckConstraint(
            "device_type IS NULL OR device_type IN ('mobile', 'desktop', 'both')",
            name="ck_content_blocks_device_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<ContentBlock {self.id} {self.entity_type}/{self.entity_id} type={self.block_type}>"
