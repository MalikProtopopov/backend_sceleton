"""Image upload service for direct file uploads to S3."""

import uuid
from uuid import UUID

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.modules.assets.service import S3Service

logger = get_logger(__name__)


class ImageUploadError(HTTPException):
    """Custom exception for image upload errors."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ImageUploadService:
    """Service for uploading images directly to S3.
    
    Handles validation, upload, and deletion of images for entities
    like articles, cases, employees, etc.
    """

    # Supported image MIME types
    ALLOWED_TYPES: set[str] = {
        "image/jpeg",
        "image/png", 
        "image/webp",
        "image/gif",
    }

    # Maximum file size in bytes (10MB)
    MAX_SIZE: int = 10 * 1024 * 1024

    # File extension mapping
    EXTENSION_MAP: dict[str, str] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    def __init__(self) -> None:
        self.s3 = S3Service()

    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file.
        
        Args:
            file: Uploaded file to validate
            
        Raises:
            ImageUploadError: If file is invalid
        """
        # Check content type
        if file.content_type not in self.ALLOWED_TYPES:
            allowed = ", ".join(sorted(self.ALLOWED_TYPES))
            raise ImageUploadError(
                f"Invalid file type: {file.content_type}. Allowed types: {allowed}"
            )

        # Check file size (if available)
        if file.size is not None and file.size > self.MAX_SIZE:
            max_mb = self.MAX_SIZE / (1024 * 1024)
            raise ImageUploadError(
                f"File too large: {file.size / (1024 * 1024):.1f}MB. Maximum size: {max_mb:.0f}MB"
            )

    def _generate_s3_key(
        self,
        tenant_id: UUID,
        folder: str,
        entity_id: UUID,
        content_type: str,
    ) -> str:
        """Generate S3 key for the image.
        
        Format: {tenant_id}/{folder}/{entity_id}.{ext}
        
        Args:
            tenant_id: Tenant UUID
            folder: Folder name (e.g., 'articles', 'employees')
            entity_id: Entity UUID
            content_type: MIME type of the image
            
        Returns:
            S3 key string
        """
        ext = self.EXTENSION_MAP.get(content_type, "jpg")
        return f"{tenant_id}/{folder}/{entity_id}.{ext}"

    def _extract_s3_key_from_url(self, image_url: str) -> str | None:
        """Extract S3 key from image URL.
        
        Supports both relative paths and full URLs (for backwards compatibility).
        
        Examples:
            - Relative: /media/tenant-id/articles/123.png -> tenant-id/articles/123.png
            - Full (S3): http://localhost:9000/bucket/tenant-id/articles/123.png
            - Full (AWS): https://bucket.s3.region.amazonaws.com/key
        
        Args:
            image_url: URL or relative path of the image
            
        Returns:
            S3 key or None if extraction fails
        """
        if not image_url:
            return None

        try:
            # Handle relative paths (new format: /media/key)
            if image_url.startswith("/media/"):
                return image_url[7:]  # len("/media/") == 7
            
            # Handle custom endpoint URLs (like Selectel/MinIO) - backwards compatibility
            if settings.s3_endpoint_url:
                prefix = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/"
                if image_url.startswith(prefix):
                    return image_url[len(prefix):]
            
            # Handle standard AWS S3 URLs - backwards compatibility
            aws_prefix = f"https://{settings.s3_bucket_name}.s3.{settings.s3_region}.amazonaws.com/"
            if image_url.startswith(aws_prefix):
                return image_url[len(aws_prefix):]

            # Fallback: try to extract key from any URL containing bucket name
            if settings.s3_bucket_name in image_url:
                parts = image_url.split(f"{settings.s3_bucket_name}/")
                if len(parts) > 1:
                    return parts[-1]

            return None
        except Exception as e:
            logger.warning("failed_to_extract_s3_key", url=image_url, error=str(e))
            return None

    async def upload_image(
        self,
        file: UploadFile,
        tenant_id: UUID,
        folder: str,
        entity_id: UUID,
        old_image_url: str | None = None,
    ) -> str:
        """Upload image to S3 and optionally delete old image.
        
        Args:
            file: Uploaded file
            tenant_id: Tenant UUID
            folder: Folder name (e.g., 'articles', 'employees')
            entity_id: Entity UUID
            old_image_url: URL of existing image to delete (optional)
            
        Returns:
            URL of the uploaded image
            
        Raises:
            ImageUploadError: If upload fails
        """
        # Validate file
        self._validate_file(file)

        # Generate S3 key
        s3_key = self._generate_s3_key(
            tenant_id=tenant_id,
            folder=folder,
            entity_id=entity_id,
            content_type=file.content_type or "image/jpeg",
        )

        try:
            # Read file content
            content = await file.read()
            
            # Double-check file size after reading
            if len(content) > self.MAX_SIZE:
                max_mb = self.MAX_SIZE / (1024 * 1024)
                raise ImageUploadError(
                    f"File too large: {len(content) / (1024 * 1024):.1f}MB. Maximum size: {max_mb:.0f}MB"
                )

            # Upload to S3
            self.s3.client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type or "image/jpeg",
            )

            # Get the URL
            new_url = self.s3.get_object_url(s3_key)

            # Delete old image if exists and different from new one
            if old_image_url:
                old_key = self._extract_s3_key_from_url(old_image_url)
                if old_key and old_key != s3_key:
                    self.s3.delete_object(old_key)
                    logger.info(
                        "old_image_deleted",
                        old_key=old_key,
                        tenant_id=str(tenant_id),
                    )

            logger.info(
                "image_uploaded",
                s3_key=s3_key,
                tenant_id=str(tenant_id),
                folder=folder,
                entity_id=str(entity_id),
                size=len(content),
            )

            return new_url

        except ImageUploadError:
            raise
        except ExternalServiceError as e:
            logger.error(
                "s3_not_configured",
                error=str(e),
                tenant_id=str(tenant_id),
            )
            raise ImageUploadError(
                "Image storage is not configured. Please contact administrator."
            )
        except Exception as e:
            logger.exception(
                "image_upload_failed",
                error=str(e),
                tenant_id=str(tenant_id),
                folder=folder,
            )
            raise ImageUploadError(f"Failed to upload image: {str(e)}")

    async def delete_image(self, image_url: str) -> bool:
        """Delete image from S3 by URL.
        
        Args:
            image_url: URL of the image to delete
            
        Returns:
            True if deletion was successful, False if image not found
        """
        if not image_url:
            return False

        s3_key = self._extract_s3_key_from_url(image_url)
        if not s3_key:
            logger.warning("could_not_extract_s3_key", url=image_url)
            return False

        try:
            self.s3.delete_object(s3_key)
            logger.info("image_deleted", s3_key=s3_key)
            return True
        except Exception as e:
            logger.exception("image_deletion_failed", error=str(e), s3_key=s3_key)
            return False


# Singleton instance for reuse
image_upload_service = ImageUploadService()

