"""Assets module database models."""

from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import (
    Base,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


class FileAsset(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """File asset stored in S3.

    Tracks all uploaded files with metadata.
    """

    __tablename__ = "file_assets"

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # S3 info
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    s3_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    # CDN URL (if using CDN)
    cdn_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Image dimensions (if applicable)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)

    # Alt text for accessibility
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Category/folder for organization
    folder: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Uploader
    uploaded_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_file_assets_tenant", "tenant_id"),
        Index("ix_file_assets_folder", "tenant_id", "folder"),
        Index("ix_file_assets_s3_key", "s3_key", unique=True),
        CheckConstraint("file_size > 0", name="ck_file_assets_size_positive"),
    )

    def __repr__(self) -> str:
        return f"<FileAsset {self.filename}>"

    @property
    def url(self) -> str:
        """Get the best available URL (CDN if available, otherwise S3)."""
        return self.cdn_url or self.s3_url

    @property
    def is_image(self) -> bool:
        """Check if file is an image."""
        return self.mime_type.startswith("image/")

