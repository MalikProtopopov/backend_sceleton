"""Mappers for transforming ORM models to DTOs in documents module.

This module provides functions to map SQLAlchemy models to Pydantic response schemas.
Keeps business logic (data transformation) out of routers.
"""

from app.core.exceptions import LocaleDataMissingError
from app.modules.documents.models import Document
from app.modules.documents.schemas import DocumentPublicResponse


def map_document_to_public_response(
    document: Document, locale: str, include_full_content: bool = True
) -> DocumentPublicResponse:
    """Map a Document model to DocumentPublicResponse.
    
    Args:
        document: Document ORM model with locales loaded
        locale: Locale code to filter by
        include_full_content: Whether to include full_description (False for lists)
        
    Returns:
        DocumentPublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in document.locales if loc.locale == locale),
        document.locales[0] if document.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Document", document.id, locale)
    
    return DocumentPublicResponse(
        id=document.id,
        slug=locale_data.slug,
        title=locale_data.title,
        excerpt=locale_data.excerpt,
        full_description=locale_data.full_description if include_full_content else None,
        file_url=document.file_url,
        document_version=document.document_version,
        document_date=document.document_date,
        published_at=document.published_at,
        meta_title=locale_data.meta_title,
        meta_description=locale_data.meta_description,
    )


def map_documents_to_public_response(
    documents: list[Document], locale: str, include_full_content: bool = False
) -> list[DocumentPublicResponse]:
    """Map a list of Document models to DocumentPublicResponse list.
    
    Note: By default, full content is not included in list views.
    """
    return [
        map_document_to_public_response(doc, locale, include_full_content)
        for doc in documents
    ]

