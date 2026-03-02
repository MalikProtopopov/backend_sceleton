"""Backward-compatible re-export. Actual code moved to app.modules.media.upload_service."""
from app.modules.media.upload_service import (  # noqa: F401
    DocumentUploadService,
    ImageUploadError,
    ImageUploadService,
    document_upload_service,
    image_upload_service,
)
