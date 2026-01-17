"""Pydantic schemas for documents module."""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentStatus(str, Enum):
    """Document status enum."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ============================================================================
# Document Locale Schemas
# ============================================================================


class DocumentLocaleBase(BaseModel):
    """Base schema for document locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    excerpt: str | None = Field(default=None, max_length=500)
    full_description: str | None = Field(
        default=None, 
        description="Full HTML description of the document"
    )
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class DocumentLocaleCreate(DocumentLocaleBase):
    """Schema for creating document locale."""

    pass


class DocumentLocaleUpdate(BaseModel):
    """Schema for updating document locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    excerpt: str | None = Field(default=None, max_length=500)
    full_description: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class DocumentLocaleResponse(DocumentLocaleBase):
    """Schema for document locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Document Schemas
# ============================================================================


class DocumentBase(BaseModel):
    """Base schema for document."""

    status: DocumentStatus = DocumentStatus.DRAFT
    document_version: str | None = Field(
        default=None, 
        max_length=50,
        description="Document version (e.g., '1.0', 'v2.3')"
    )
    document_date: date | None = Field(
        default=None,
        description="Date of the document"
    )
    sort_order: int = 0


class DocumentCreate(DocumentBase):
    """Schema for creating a document.
    
    Note: file_url is managed via POST /admin/documents/{id}/file endpoint.
    """

    locales: list[DocumentLocaleCreate] = Field(..., min_length=1)


class DocumentUpdate(BaseModel):
    """Schema for updating a document.
    
    Note: file_url is managed via POST/DELETE /admin/documents/{id}/file endpoints.
    """

    status: DocumentStatus | None = None
    document_version: str | None = Field(default=None, max_length=50)
    document_date: date | None = None
    sort_order: int | None = None
    locales: list[DocumentLocaleUpdate] | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class DocumentResponse(DocumentBase):
    """Schema for document response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    file_url: str | None = None
    version: int
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    locales: list[DocumentLocaleResponse] = []


class DocumentPublicResponse(BaseModel):
    """Schema for public document response."""

    id: UUID
    slug: str
    title: str
    excerpt: str | None = None
    full_description: str | None = None
    file_url: str | None = None
    document_version: str | None = None
    document_date: date | None = None
    published_at: datetime | None = None
    meta_title: str | None = None
    meta_description: str | None = None


class DocumentListResponse(BaseModel):
    """Schema for document list response."""

    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentPublicListResponse(BaseModel):
    """Schema for public document list response."""

    items: list[DocumentPublicResponse]
    total: int
    page: int
    page_size: int

