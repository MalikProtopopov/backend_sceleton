"""API routes for documents module."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Locale, Pagination, PublicTenantId
from app.core.image_upload import image_upload_service
from app.core.security import PermissionChecker, get_current_tenant_id
from app.modules.documents.models import DocumentStatus
from app.modules.documents.schemas import (
    DocumentCreate,
    DocumentListResponse,
    DocumentPublicListResponse,
    DocumentPublicResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.modules.documents.mappers import (
    map_document_to_public_response,
    map_documents_to_public_response,
)
from app.modules.documents.service import DocumentService

router = APIRouter()


# ============================================================================
# Public Routes - Documents
# ============================================================================


@router.get(
    "/public/documents",
    response_model=DocumentPublicListResponse,
    summary="List published documents",
    tags=["Public - Documents"],
)
async def list_documents_public(
    locale: Locale,
    pagination: Pagination,
    tenant_id: PublicTenantId,
    search: str | None = Query(default=None, description="Search in title"),
    document_date_from: date | None = Query(default=None, description="Filter by date from"),
    document_date_to: date | None = Query(default=None, description="Filter by date to"),
    db: AsyncSession = Depends(get_db),
) -> DocumentPublicListResponse:
    """List published documents for public display."""
    service = DocumentService(db)
    documents, total = await service.list_published(
        tenant_id=tenant_id,
        locale=locale.locale,
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        document_date_from=document_date_from,
        document_date_to=document_date_to,
    )

    items = map_documents_to_public_response(documents, locale.locale, include_full_content=False)

    return DocumentPublicListResponse(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get(
    "/public/documents/{slug}",
    response_model=DocumentPublicResponse,
    summary="Get document by slug",
    tags=["Public - Documents"],
)
async def get_document_by_slug(
    slug: str,
    locale: Locale,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> DocumentPublicResponse:
    """Get a published document by slug."""
    service = DocumentService(db)
    doc = await service.get_by_slug(slug, locale.locale, tenant_id)
    return map_document_to_public_response(doc, locale.locale, include_full_content=True)


# ============================================================================
# Admin Routes - Documents
# ============================================================================


@router.get(
    "/admin/documents",
    response_model=DocumentListResponse,
    summary="List documents",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:read"))],
)
async def list_documents(
    pagination: Pagination,
    tenant_id: UUID = Depends(get_current_tenant_id),
    status: DocumentStatus | None = Query(default=None, description="Filter by status"),
    search: str | None = Query(default=None, description="Search in title"),
    document_date_from: date | None = Query(default=None, description="Filter by date from"),
    document_date_to: date | None = Query(default=None, description="Filter by date to"),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_direction: str = Query(default="desc", description="Sort direction (asc/desc)"),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List all documents for admin."""
    service = DocumentService(db)
    documents, total = await service.list_documents(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        status=status.value if status else None,
        search=search,
        document_date_from=document_date_from,
        document_date_to=document_date_to,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create document",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:create"))],
)
async def create_document(
    data: DocumentCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Create a new document."""
    service = DocumentService(db)
    document = await service.create(tenant_id, data)
    return DocumentResponse.model_validate(document)


@router.get(
    "/admin/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:read"))],
)
async def get_document(
    document_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get a document by ID."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id, tenant_id)
    return DocumentResponse.model_validate(document)


@router.patch(
    "/admin/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Update document",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:update"))],
)
async def update_document(
    document_id: UUID,
    data: DocumentUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Update a document."""
    service = DocumentService(db)
    document = await service.update(document_id, tenant_id, data)
    await db.refresh(document)
    await db.refresh(document, ["locales"])
    return DocumentResponse.model_validate(document)


@router.delete(
    "/admin/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:delete"))],
)
async def delete_document(
    document_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a document."""
    service = DocumentService(db)
    await service.soft_delete(document_id, tenant_id)


@router.post(
    "/admin/documents/{document_id}/publish",
    response_model=DocumentResponse,
    summary="Publish document",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:update"))],
)
async def publish_document(
    document_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Publish a document."""
    service = DocumentService(db)
    document = await service.publish(document_id, tenant_id)
    await db.refresh(document)
    await db.refresh(document, ["locales"])
    return DocumentResponse.model_validate(document)


@router.post(
    "/admin/documents/{document_id}/unpublish",
    response_model=DocumentResponse,
    summary="Unpublish document",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:update"))],
)
async def unpublish_document(
    document_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Unpublish a document (move to draft)."""
    service = DocumentService(db)
    document = await service.unpublish(document_id, tenant_id)
    await db.refresh(document)
    await db.refresh(document, ["locales"])
    return DocumentResponse.model_validate(document)


# ============================================================================
# File Upload Routes
# ============================================================================


@router.post(
    "/admin/documents/{document_id}/file",
    response_model=DocumentResponse,
    summary="Upload document file",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:update"))],
)
async def upload_document_file(
    document_id: UUID,
    file: UploadFile = File(...),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a file for a document (PDF, DOC, etc.)."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id, tenant_id)

    # Upload file to S3
    file_url = await image_upload_service.upload_image(
        file=file,
        tenant_id=tenant_id,
        folder="documents",
        entity_id=document_id,
        old_image_url=document.file_url,
    )

    # Update document
    document.file_url = file_url
    await db.commit()
    await db.refresh(document, ["locales"])

    return DocumentResponse.model_validate(document)


@router.delete(
    "/admin/documents/{document_id}/file",
    response_model=DocumentResponse,
    summary="Delete document file",
    tags=["Admin - Documents"],
    dependencies=[Depends(PermissionChecker("documents:update"))],
)
async def delete_document_file(
    document_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Delete the file associated with a document."""
    service = DocumentService(db)
    document = await service.get_by_id(document_id, tenant_id)

    if document.file_url:
        # Delete from S3
        await image_upload_service.delete_image(document.file_url)
        document.file_url = None
        await db.commit()

    await db.refresh(document, ["locales"])
    return DocumentResponse.model_validate(document)

