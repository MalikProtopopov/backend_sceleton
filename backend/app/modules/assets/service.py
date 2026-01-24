"""Assets module service layer."""

import uuid
from datetime import datetime
from uuid import UUID

import boto3
from botocore.config import Config
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.database import transactional
from app.core.exceptions import ExternalServiceError, NotFoundError
from app.core.logging import get_logger
from app.modules.assets.models import FileAsset
from app.modules.assets.schemas import FileAssetCreate, FileAssetUpdate

logger = get_logger(__name__)


class S3Service:
    """Service for S3 operations."""

    def __init__(self) -> None:
        self._client = None
        self._public_client = None

    @property
    def is_configured(self) -> bool:
        """Check if S3 credentials are configured."""
        return bool(settings.s3_access_key and settings.s3_secret_key)

    @property
    def client(self):
        """Get or create S3 client for internal operations.
        
        Raises:
            ExternalServiceError: If S3 credentials are not configured.
        """
        if not self.is_configured:
            raise ExternalServiceError(
                "S3",
                "S3 credentials not configured. Set S3_ACCESS_KEY and S3_SECRET_KEY environment variables."
            )
        
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url or None,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    @property
    def public_client(self):
        """Get or create S3 client for generating presigned URLs.
        
        Uses S3_PUBLIC_URL as endpoint so signatures are valid for browser requests.
        Falls back to internal client if S3_PUBLIC_URL is not configured.
        """
        if not settings.s3_public_url:
            return self.client
        
        if self._public_client is None:
            self._public_client = boto3.client(
                "s3",
                endpoint_url=settings.s3_public_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=Config(signature_version="s3v4"),
            )
        return self._public_client

    def generate_presigned_upload_url(
        self,
        s3_key: str,
        content_type: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for direct upload to S3.
        
        Uses public_client to generate URLs with correct host for browser requests.
        The signature is calculated with the public endpoint URL.
        """
        try:
            url = self.public_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.s3_bucket_name,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.exception("s3_presign_failed", error=str(e))
            raise ExternalServiceError("S3", "Failed to generate upload URL")

    def get_object_url(self, s3_key: str) -> str:
        """Get public URL for an S3 object.
        
        Returns relative path (e.g., /media/tenant-id/articles/...).
        Frontend should prepend the appropriate base URL (API server, CDN, etc.).
        """
        # Возвращаем относительный путь
        # Фронтенд сам добавит базовый URL (CDN, прокси и т.д.)
        return f"/media/{s3_key}"

    def delete_object(self, s3_key: str) -> None:
        """Delete object from S3."""
        try:
            self.client.delete_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
            )
        except Exception as e:
            logger.exception("s3_delete_failed", error=str(e), key=s3_key)
            # Don't raise - deletion failure shouldn't break the flow


class FileAssetService:
    """Service for managing file assets."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.s3 = S3Service()

    async def get_by_id(self, asset_id: UUID, tenant_id: UUID) -> FileAsset:
        """Get file asset by ID."""
        stmt = (
            select(FileAsset)
            .where(FileAsset.id == asset_id)
            .where(FileAsset.tenant_id == tenant_id)
            .where(FileAsset.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        asset = result.scalar_one_or_none()

        if not asset:
            raise NotFoundError("FileAsset", asset_id)

        return asset

    async def list_assets(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        folder: str | None = None,
        mime_type_prefix: str | None = None,
    ) -> tuple[list[FileAsset], int]:
        """List file assets with pagination."""
        base_query = (
            select(FileAsset)
            .where(FileAsset.tenant_id == tenant_id)
            .where(FileAsset.deleted_at.is_(None))
        )

        if folder:
            base_query = base_query.where(FileAsset.folder == folder)

        if mime_type_prefix:
            base_query = base_query.where(
                FileAsset.mime_type.startswith(mime_type_prefix)
            )

        # Count
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get results
        stmt = (
            base_query.order_by(FileAsset.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        assets = list(result.scalars().all())

        return assets, total

    def generate_upload_url(
        self,
        tenant_id: UUID,
        filename: str,
        content_type: str,
        folder: str | None = None,
    ) -> tuple[str, str, str]:
        """Generate presigned URL for upload.

        Returns:
            Tuple of (upload_url, file_url, s3_key)
        """
        # Generate unique S3 key
        file_uuid = str(uuid.uuid4())
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

        # Build key: tenant_id/folder/uuid.ext
        key_parts = [str(tenant_id)]
        if folder:
            key_parts.append(folder)
        key_parts.append(f"{file_uuid}.{ext}" if ext else file_uuid)

        s3_key = "/".join(key_parts)

        # Generate URLs
        upload_url = self.s3.generate_presigned_upload_url(s3_key, content_type)
        file_url = self.s3.get_object_url(s3_key)

        return upload_url, file_url, s3_key

    @transactional
    async def create(self, tenant_id: UUID, data: FileAssetCreate) -> FileAsset:
        """Create file asset record after upload."""
        asset = FileAsset(tenant_id=tenant_id, **data.model_dump())
        self.db.add(asset)
        await self.db.flush()
        await self.db.refresh(asset)

        logger.info(
            "file_asset_created",
            asset_id=str(asset.id),
            tenant_id=str(tenant_id),
            filename=asset.filename,
            size=asset.file_size,
        )

        return asset

    @transactional
    async def update(
        self, asset_id: UUID, tenant_id: UUID, data: FileAssetUpdate
    ) -> FileAsset:
        """Update file asset metadata."""
        asset = await self.get_by_id(asset_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(asset, field, value)

        await self.db.flush()
        await self.db.refresh(asset)

        return asset

    @transactional
    async def soft_delete(self, asset_id: UUID, tenant_id: UUID) -> None:
        """Soft delete file asset.

        Note: Does not delete from S3 immediately.
        Use a background job to clean up orphaned S3 objects.
        """
        asset = await self.get_by_id(asset_id, tenant_id)
        asset.soft_delete()
        await self.db.flush()

        logger.info(
            "file_asset_deleted",
            asset_id=str(asset_id),
            tenant_id=str(tenant_id),
            s3_key=asset.s3_key,
        )

    @transactional
    async def hard_delete(self, asset_id: UUID, tenant_id: UUID) -> None:
        """Hard delete file asset and remove from S3."""
        asset = await self.get_by_id(asset_id, tenant_id)

        # Delete from S3
        self.s3.delete_object(asset.s3_key)

        # Delete from database
        await self.db.delete(asset)
        await self.db.flush()

        logger.info(
            "file_asset_hard_deleted",
            asset_id=str(asset_id),
            tenant_id=str(tenant_id),
            s3_key=asset.s3_key,
        )

