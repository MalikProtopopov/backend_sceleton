"""Base SQLAlchemy models with common mixins."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(
            ["_" + c.lower() if c.isupper() else c for c in name]
        ).lstrip("_") + "s"


class UUIDMixin:
    """Mixin that adds UUID primary key."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality.

    CRITICAL for SEO: Never hard-delete content that might have external links.
    Soft delete preserves URL integrity and allows recovery.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.deleted_at = datetime.now(UTC)

    def restore(self) -> None:
        """Restore soft-deleted record."""
        self.deleted_at = None


class VersionMixin:
    """Mixin for optimistic locking using version field.

    Prevents lost updates in concurrent editing scenarios.
    
    Usage in services:
        entity.check_version(data.version)  # Validates and auto-increments
    """

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    def check_version(self, provided_version: int) -> None:
        """Validate version and increment for optimistic locking.
        
        Args:
            provided_version: Version from client request
            
        Raises:
            VersionConflictError: If versions don't match
        """
        # Import here to avoid circular imports
        from app.core.exceptions import VersionConflictError
        
        if self.version != provided_version:
            raise VersionConflictError(
                self.__class__.__name__, 
                self.version, 
                provided_version
            )
        self.version += 1


class TenantMixin:
    """Mixin that adds tenant_id for multi-tenancy support.
    
    Note: This creates the column only. For models that need a relationship
    to Tenant, you must define the ForeignKey explicitly in the model.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(
            UUID(as_uuid=True),
            nullable=False,
            index=True,
        )


class SlugMixin:
    """Mixin for URL-friendly slugs."""

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )


class SEOMixin:
    """Mixin for basic SEO fields."""

    meta_title: Mapped[str | None] = mapped_column(String(70), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    meta_keywords: Mapped[str | None] = mapped_column(String(255), nullable=True)
    og_image: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SortOrderMixin:
    """Mixin for manual ordering of records."""

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )


class PublishableMixin:
    """Mixin for content with publish status."""

    is_published: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )



