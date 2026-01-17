"""API routes for assets module."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import get_db
from app.core.dependencies import Pagination
from app.core.exceptions import FileNotFoundInStorageError
from app.core.logging import get_logger
from app.core.security import PermissionChecker, get_current_active_user, get_current_tenant_id
from app.modules.assets.schemas import (
    FileAssetCreate,
    FileAssetListResponse,
    FileAssetResponse,
    FileAssetUpdate,
    UploadURLRequest,
    UploadURLResponse,
)
from app.modules.assets.service import FileAssetService, S3Service
from app.modules.auth.models import AdminUser

logger = get_logger(__name__)
router = APIRouter()

# Separate router for public media (mounted at root level, not under /api/v1)
media_router = APIRouter()


# ============================================================================
# Admin Routes
# ============================================================================


@router.get(
    "/admin/files",
    response_model=FileAssetListResponse,
    summary="List files",
    tags=["Admin - Assets"],
    dependencies=[Depends(PermissionChecker("settings:read"))],
)
async def list_files(
    pagination: Pagination,
    folder: str | None = Query(default=None),
    images_only: bool = Query(default=False, alias="imagesOnly"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FileAssetListResponse:
    """List all uploaded files."""
    service = FileAssetService(db)
    assets, total = await service.list_assets(
        tenant_id=tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        folder=folder,
        mime_type_prefix="image/" if images_only else None,
    )

    return FileAssetListResponse(
        items=[FileAssetResponse.model_validate(a) for a in assets],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post(
    "/admin/files/upload-url",
    response_model=UploadURLResponse,
    summary="Get presigned upload URL",
    tags=["Admin - Assets"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def get_upload_url(
    data: UploadURLRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UploadURLResponse:
    """Get a presigned URL for direct upload to S3.

    Usage:
    1. Call this endpoint to get upload_url
    2. PUT file directly to upload_url
    3. Call POST /admin/files to register the uploaded file
    """
    service = FileAssetService(db)
    upload_url, file_url, s3_key = service.generate_upload_url(
        tenant_id=tenant_id,
        filename=data.filename,
        content_type=data.content_type,
        folder=data.folder,
    )

    return UploadURLResponse(
        upload_url=upload_url,
        file_url=file_url,
        s3_key=s3_key,
        expires_in=3600,
    )


@router.post(
    "/admin/files",
    response_model=FileAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register uploaded file",
    tags=["Admin - Assets"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def register_file(
    data: FileAssetCreate,
    user: AdminUser = Depends(get_current_active_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FileAssetResponse:
    """Register a file that was uploaded directly to S3.

    Call this after successfully uploading to the presigned URL.
    """
    # Set uploaded_by if not provided
    if data.uploaded_by is None:
        data.uploaded_by = user.id

    service = FileAssetService(db)
    asset = await service.create(tenant_id, data)
    return FileAssetResponse.model_validate(asset)


@router.get(
    "/admin/files/{file_id}",
    response_model=FileAssetResponse,
    summary="Get file",
    tags=["Admin - Assets"],
    dependencies=[Depends(PermissionChecker("settings:read"))],
)
async def get_file(
    file_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FileAssetResponse:
    """Get file asset by ID."""
    service = FileAssetService(db)
    asset = await service.get_by_id(file_id, tenant_id)
    return FileAssetResponse.model_validate(asset)


@router.patch(
    "/admin/files/{file_id}",
    response_model=FileAssetResponse,
    summary="Update file metadata",
    tags=["Admin - Assets"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def update_file(
    file_id: UUID,
    data: FileAssetUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> FileAssetResponse:
    """Update file metadata (alt text, folder)."""
    service = FileAssetService(db)
    asset = await service.update(file_id, tenant_id, data)
    return FileAssetResponse.model_validate(asset)


@router.delete(
    "/admin/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete file",
    tags=["Admin - Assets"],
    dependencies=[Depends(PermissionChecker("settings:update"))],
)
async def delete_file(
    file_id: UUID,
    hard_delete: bool = Query(default=False, alias="hardDelete"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a file.

    By default, soft deletes. Set hardDelete=true to also remove from S3.
    """
    service = FileAssetService(db)

    if hard_delete:
        await service.hard_delete(file_id, tenant_id)
    else:
        await service.soft_delete(file_id, tenant_id)


# ============================================================================
# Public Media Routes (No Auth Required)
# ============================================================================


@media_router.get(
    "/{path:path}",
    summary="Serve media file",
    tags=["Public - Media"],
    responses={
        200: {"description": "File content"},
        404: {"description": "File not found"},
    },
)
async def serve_media(path: str) -> Response:
    """Serve media files from S3 storage.
    
    This endpoint proxies requests to S3, allowing frontend to use relative URLs.
    Files are cached by the browser using Cache-Control headers.
    
    Path format: /media/{tenant_id}/{folder}/{filename}
    Example: /media/abc123/articles/image.png
    """
    try:
        s3 = S3Service()
        
        # Get object from S3
        response = s3.client.get_object(
            Bucket=settings.s3_bucket_name,
            Key=path,
        )
        
        content_type = response.get("ContentType", "application/octet-stream")
        body = response["Body"].read()
        
        return Response(
            content=body,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=31536000",  # 1 year cache
                "Content-Length": str(len(body)),
            },
        )
        
    except s3.client.exceptions.NoSuchKey:
        raise FileNotFoundInStorageError(path)
    except Exception as e:
        logger.error("media_serve_error", path=path, error=str(e))
        raise FileNotFoundInStorageError(path)

