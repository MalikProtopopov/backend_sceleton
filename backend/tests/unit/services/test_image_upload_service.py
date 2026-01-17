"""Unit tests for ImageUploadService.

Tests the image upload service with mocked S3 operations.
Following TEST_RECOMENDATIONS.md structure.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.core.image_upload import ImageUploadError, ImageUploadService


class TestImageUploadServiceValidation:
    """Tests for file validation logic."""

    @pytest.fixture
    def service(self) -> ImageUploadService:
        """Create service with mocked S3."""
        with patch("app.core.image_upload.S3Service") as mock_s3:
            mock_s3.return_value.is_configured = True
            service = ImageUploadService()
            return service

    def test_allowed_types_are_defined(self, service: ImageUploadService):
        """Test that allowed types are properly defined."""
        expected_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        assert service.ALLOWED_TYPES == expected_types

    def test_max_size_is_10mb(self, service: ImageUploadService):
        """Test that max size is 10MB."""
        expected_size = 10 * 1024 * 1024  # 10MB
        assert service.MAX_SIZE == expected_size

    def test_validate_file_valid_jpeg(self, service: ImageUploadService):
        """Test validation passes for valid JPEG."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = 1024 * 1024  # 1MB

        # Should not raise
        service._validate_file(mock_file)

    def test_validate_file_valid_png(self, service: ImageUploadService):
        """Test validation passes for valid PNG."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/png"
        mock_file.size = 5 * 1024 * 1024  # 5MB

        service._validate_file(mock_file)

    def test_validate_file_valid_webp(self, service: ImageUploadService):
        """Test validation passes for valid WebP."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/webp"
        mock_file.size = 2 * 1024 * 1024  # 2MB

        service._validate_file(mock_file)

    def test_validate_file_valid_gif(self, service: ImageUploadService):
        """Test validation passes for valid GIF."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/gif"
        mock_file.size = 3 * 1024 * 1024  # 3MB

        service._validate_file(mock_file)

    def test_validate_file_rejects_pdf(self, service: ImageUploadService):
        """Test validation fails for PDF file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "application/pdf"
        mock_file.size = 1024

        with pytest.raises(ImageUploadError) as exc_info:
            service._validate_file(mock_file)

        assert "Invalid file type" in str(exc_info.value.detail)
        assert "application/pdf" in str(exc_info.value.detail)

    def test_validate_file_rejects_text(self, service: ImageUploadService):
        """Test validation fails for text file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "text/plain"
        mock_file.size = 100

        with pytest.raises(ImageUploadError) as exc_info:
            service._validate_file(mock_file)

        assert "Invalid file type" in str(exc_info.value.detail)

    def test_validate_file_rejects_too_large(self, service: ImageUploadService):
        """Test validation fails for file exceeding 10MB."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = 15 * 1024 * 1024  # 15MB

        with pytest.raises(ImageUploadError) as exc_info:
            service._validate_file(mock_file)

        assert "File too large" in str(exc_info.value.detail)
        assert "15" in str(exc_info.value.detail)  # Shows actual size

    def test_validate_file_allows_exactly_10mb(self, service: ImageUploadService):
        """Test validation passes for exactly 10MB file."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = 10 * 1024 * 1024  # Exactly 10MB

        # Should not raise
        service._validate_file(mock_file)

    def test_validate_file_handles_none_size(self, service: ImageUploadService):
        """Test validation works when size is None (not yet known)."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = None

        # Should not raise - size will be checked after reading
        service._validate_file(mock_file)


class TestImageUploadServiceS3Key:
    """Tests for S3 key generation."""

    @pytest.fixture
    def service(self) -> ImageUploadService:
        """Create service with mocked S3."""
        with patch("app.core.image_upload.S3Service"):
            return ImageUploadService()

    def test_generate_s3_key_jpeg(self, service: ImageUploadService):
        """Test S3 key generation for JPEG."""
        tenant_id = uuid4()
        entity_id = uuid4()

        key = service._generate_s3_key(
            tenant_id=tenant_id,
            folder="articles",
            entity_id=entity_id,
            content_type="image/jpeg",
        )

        assert key == f"{tenant_id}/articles/{entity_id}.jpg"

    def test_generate_s3_key_png(self, service: ImageUploadService):
        """Test S3 key generation for PNG."""
        tenant_id = uuid4()
        entity_id = uuid4()

        key = service._generate_s3_key(
            tenant_id=tenant_id,
            folder="employees",
            entity_id=entity_id,
            content_type="image/png",
        )

        assert key == f"{tenant_id}/employees/{entity_id}.png"

    def test_generate_s3_key_webp(self, service: ImageUploadService):
        """Test S3 key generation for WebP."""
        tenant_id = uuid4()
        entity_id = uuid4()

        key = service._generate_s3_key(
            tenant_id=tenant_id,
            folder="cases",
            entity_id=entity_id,
            content_type="image/webp",
        )

        assert key == f"{tenant_id}/cases/{entity_id}.webp"

    def test_generate_s3_key_gif(self, service: ImageUploadService):
        """Test S3 key generation for GIF."""
        tenant_id = uuid4()
        entity_id = uuid4()

        key = service._generate_s3_key(
            tenant_id=tenant_id,
            folder="reviews",
            entity_id=entity_id,
            content_type="image/gif",
        )

        assert key == f"{tenant_id}/reviews/{entity_id}.gif"

    def test_generate_s3_key_unknown_type_defaults_to_jpg(self, service: ImageUploadService):
        """Test S3 key defaults to .jpg for unknown type."""
        tenant_id = uuid4()
        entity_id = uuid4()

        key = service._generate_s3_key(
            tenant_id=tenant_id,
            folder="articles",
            entity_id=entity_id,
            content_type="image/unknown",
        )

        assert key.endswith(".jpg")


class TestImageUploadServiceExtractKey:
    """Tests for extracting S3 key from URL."""

    @pytest.fixture
    def service(self) -> ImageUploadService:
        """Create service with mocked S3."""
        with patch("app.core.image_upload.S3Service"):
            return ImageUploadService()

    def test_extract_key_from_empty_url(self, service: ImageUploadService):
        """Test extracting key from empty URL returns None."""
        assert service._extract_s3_key_from_url("") is None
        assert service._extract_s3_key_from_url(None) is None

    @patch("app.core.image_upload.settings")
    def test_extract_key_from_custom_endpoint_url(
        self, mock_settings, service: ImageUploadService
    ):
        """Test extracting key from custom S3 endpoint URL."""
        mock_settings.s3_endpoint_url = "https://s3.example.com"
        mock_settings.s3_bucket_name = "my-bucket"
        mock_settings.s3_region = "us-east-1"

        url = "https://s3.example.com/my-bucket/tenant-123/articles/image-456.jpg"
        key = service._extract_s3_key_from_url(url)

        assert key == "tenant-123/articles/image-456.jpg"

    @patch("app.core.image_upload.settings")
    def test_extract_key_from_aws_url(
        self, mock_settings, service: ImageUploadService
    ):
        """Test extracting key from standard AWS S3 URL."""
        mock_settings.s3_endpoint_url = ""  # No custom endpoint
        mock_settings.s3_bucket_name = "my-bucket"
        mock_settings.s3_region = "us-east-1"

        url = "https://my-bucket.s3.us-east-1.amazonaws.com/tenant-123/articles/image-456.jpg"
        key = service._extract_s3_key_from_url(url)

        assert key == "tenant-123/articles/image-456.jpg"

    def test_extract_key_from_relative_url(self, service: ImageUploadService):
        """Test extracting key from relative /media/ URL."""
        url = "/media/tenant-123/articles/image-456.jpg"
        key = service._extract_s3_key_from_url(url)

        assert key == "tenant-123/articles/image-456.jpg"

    def test_extract_key_from_relative_url_nested(self, service: ImageUploadService):
        """Test extracting key from nested relative /media/ URL."""
        url = "/media/abc-123/employees/photos/headshot.png"
        key = service._extract_s3_key_from_url(url)

        assert key == "abc-123/employees/photos/headshot.png"

    @patch("app.core.image_upload.settings")
    def test_extract_key_from_unrecognized_url(
        self, mock_settings, service: ImageUploadService
    ):
        """Test extracting key from unrecognized URL returns None."""
        mock_settings.s3_endpoint_url = "https://s3.example.com"
        mock_settings.s3_bucket_name = "my-bucket"
        mock_settings.s3_region = "us-east-1"

        url = "https://other-service.com/some/path/image.jpg"
        key = service._extract_s3_key_from_url(url)

        assert key is None


class TestImageUploadServiceUpload:
    """Tests for image upload functionality."""

    @pytest.fixture
    def mock_s3_service(self):
        """Create mock S3 service."""
        mock = MagicMock()
        mock.is_configured = True
        mock.client = MagicMock()
        mock.get_object_url.return_value = "https://s3.example.com/bucket/test.jpg"
        return mock

    @pytest.fixture
    def service(self, mock_s3_service) -> ImageUploadService:
        """Create service with mocked S3."""
        with patch("app.core.image_upload.S3Service", return_value=mock_s3_service):
            return ImageUploadService()

    @pytest.mark.asyncio
    async def test_upload_image_success(self, service: ImageUploadService, mock_s3_service):
        """Test successful image upload."""
        tenant_id = uuid4()
        entity_id = uuid4()
        file_content = b"fake image content"

        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = len(file_content)
        mock_file.read = AsyncMock(return_value=file_content)

        service.s3 = mock_s3_service

        url = await service.upload_image(
            file=mock_file,
            tenant_id=tenant_id,
            folder="articles",
            entity_id=entity_id,
        )

        # Verify S3 was called
        mock_s3_service.client.put_object.assert_called_once()
        call_args = mock_s3_service.client.put_object.call_args
        assert call_args.kwargs["Body"] == file_content
        assert call_args.kwargs["ContentType"] == "image/jpeg"

        # Verify URL returned
        assert url == "https://s3.example.com/bucket/test.jpg"

    @pytest.mark.asyncio
    async def test_upload_image_deletes_old_image(
        self, service: ImageUploadService, mock_s3_service
    ):
        """Test that upload deletes old image when provided."""
        tenant_id = uuid4()
        entity_id = uuid4()
        file_content = b"new image content"
        old_url = "https://s3.example.com/bucket/old-image.jpg"

        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = len(file_content)
        mock_file.read = AsyncMock(return_value=file_content)

        service.s3 = mock_s3_service

        with patch.object(
            service, "_extract_s3_key_from_url", return_value="old-key.jpg"
        ):
            await service.upload_image(
                file=mock_file,
                tenant_id=tenant_id,
                folder="articles",
                entity_id=entity_id,
                old_image_url=old_url,
            )

        # Verify old image was deleted
        mock_s3_service.delete_object.assert_called_once_with("old-key.jpg")

    @pytest.mark.asyncio
    async def test_upload_image_rejects_large_file_after_read(
        self, service: ImageUploadService, mock_s3_service
    ):
        """Test that upload rejects file if too large after reading."""
        tenant_id = uuid4()
        entity_id = uuid4()
        # Create content larger than 10MB
        file_content = b"x" * (11 * 1024 * 1024)

        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = None  # Size unknown initially
        mock_file.read = AsyncMock(return_value=file_content)

        service.s3 = mock_s3_service

        with pytest.raises(ImageUploadError) as exc_info:
            await service.upload_image(
                file=mock_file,
                tenant_id=tenant_id,
                folder="articles",
                entity_id=entity_id,
            )

        assert "File too large" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_image_handles_s3_error(
        self, service: ImageUploadService, mock_s3_service
    ):
        """Test that upload handles S3 errors gracefully."""
        tenant_id = uuid4()
        entity_id = uuid4()
        file_content = b"fake image content"

        mock_file = MagicMock(spec=UploadFile)
        mock_file.content_type = "image/jpeg"
        mock_file.size = len(file_content)
        mock_file.read = AsyncMock(return_value=file_content)

        # Make S3 fail
        mock_s3_service.client.put_object.side_effect = Exception("S3 error")
        service.s3 = mock_s3_service

        with pytest.raises(ImageUploadError) as exc_info:
            await service.upload_image(
                file=mock_file,
                tenant_id=tenant_id,
                folder="articles",
                entity_id=entity_id,
            )

        assert "Failed to upload image" in str(exc_info.value.detail)


class TestImageUploadServiceDelete:
    """Tests for image deletion functionality."""

    @pytest.fixture
    def mock_s3_service(self):
        """Create mock S3 service."""
        mock = MagicMock()
        mock.is_configured = True
        return mock

    @pytest.fixture
    def service(self, mock_s3_service) -> ImageUploadService:
        """Create service with mocked S3."""
        with patch("app.core.image_upload.S3Service", return_value=mock_s3_service):
            return ImageUploadService()

    @pytest.mark.asyncio
    async def test_delete_image_success(
        self, service: ImageUploadService, mock_s3_service
    ):
        """Test successful image deletion."""
        service.s3 = mock_s3_service

        with patch.object(
            service, "_extract_s3_key_from_url", return_value="tenant/folder/image.jpg"
        ):
            result = await service.delete_image(
                "https://s3.example.com/bucket/tenant/folder/image.jpg"
            )

        assert result is True
        mock_s3_service.delete_object.assert_called_once_with("tenant/folder/image.jpg")

    @pytest.mark.asyncio
    async def test_delete_image_empty_url(self, service: ImageUploadService):
        """Test delete returns False for empty URL."""
        result = await service.delete_image("")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_image_none_url(self, service: ImageUploadService):
        """Test delete returns False for None URL."""
        result = await service.delete_image(None)
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_image_unrecognized_url(
        self, service: ImageUploadService, mock_s3_service
    ):
        """Test delete returns False for unrecognized URL."""
        service.s3 = mock_s3_service

        with patch.object(service, "_extract_s3_key_from_url", return_value=None):
            result = await service.delete_image("https://other-service.com/image.jpg")

        assert result is False
        mock_s3_service.delete_object.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_image_handles_s3_error(
        self, service: ImageUploadService, mock_s3_service
    ):
        """Test delete handles S3 errors gracefully."""
        mock_s3_service.delete_object.side_effect = Exception("S3 delete error")
        service.s3 = mock_s3_service

        with patch.object(
            service, "_extract_s3_key_from_url", return_value="key.jpg"
        ):
            result = await service.delete_image("https://s3.example.com/bucket/key.jpg")

        # Should return False on error, not raise
        assert result is False

