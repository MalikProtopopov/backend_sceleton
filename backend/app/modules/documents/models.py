"""Documents module database models."""

from datetime import UTC, date, datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import (
    Base,
    SEOMixin,
    SlugMixin,
    SoftDeleteMixin,
    SortOrderMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


class DocumentStatus(str, Enum):
    """Document publication status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Document(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Document model - legal and corporate documents with localization."""

    __tablename__ = "documents"

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=DocumentStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    # Document metadata
    document_version: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True,
        comment="Document version (e.g., '1.0', 'v2.3')"
    )
    document_date: Mapped[date | None] = mapped_column(
        Date, 
        nullable=True,
        comment="Date of the document"
    )

    # Publishing
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )

    # File reference (optional - for file upload)
    file_url: Mapped[str | None] = mapped_column(
        String(500), 
        nullable=True,
        comment="URL to document file (PDF, etc.)"
    )

    # Relations
    locales: Mapped[list["DocumentLocale"]] = relationship(
        "DocumentLocale",
        back_populates="document",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_documents_tenant", "tenant_id"),
        Index(
            "ix_documents_published",
            "tenant_id",
            "status",
            postgresql_where="deleted_at IS NULL AND status = 'published'",
        ),
        Index("ix_documents_date", "document_date"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_documents_status",
        ),
    )

    @property
    def is_published(self) -> bool:
        """Check if document is published."""
        return self.status == DocumentStatus.PUBLISHED.value

    def publish(self) -> None:
        """Publish the document."""
        self.status = DocumentStatus.PUBLISHED.value
        if not self.published_at:
            self.published_at = datetime.now(UTC)

    def unpublish(self) -> None:
        """Move document to draft."""
        self.status = DocumentStatus.DRAFT.value

    def archive(self) -> None:
        """Archive the document."""
        self.status = DocumentStatus.ARCHIVED.value

    def __repr__(self) -> str:
        return f"<Document {self.id} status={self.status}>"


class DocumentLocale(Base, UUIDMixin, TimestampMixin, SlugMixin, SEOMixin):
    """Localized content for documents."""

    __tablename__ = "document_locales"

    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(
        String(500), 
        nullable=True,
        comment="Short description / summary"
    )
    full_description: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="Full HTML description of the document"
    )

    # Relation
    document: Mapped["Document"] = relationship("Document", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("document_id", "locale", name="uq_document_locales"),
        Index("ix_document_locales_slug", "locale", "slug"),
        CheckConstraint("char_length(title) >= 1", name="ck_document_locales_title"),
        CheckConstraint("char_length(slug) >= 2", name="ck_document_locales_slug"),
    )

    def __repr__(self) -> str:
        return f"<DocumentLocale {self.id} locale={self.locale}>"

