"""Core module - foundational components."""

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.core.base_service import BaseService, update_many_to_many
from app.core.pagination import paginate_query, paginate, PaginatedResult
from app.core.url_utils import (
    normalize_path,
    normalize_url,
    validate_base_url,
    build_sitemap_url,
    extract_domain,
    is_same_domain,
)

__all__ = [
    "get_db",
    "AppException",
    "get_logger",
    "BaseService",
    "update_many_to_many",
    "paginate_query",
    "paginate",
    "PaginatedResult",
    "normalize_path",
    "normalize_url",
    "validate_base_url",
    "build_sitemap_url",
    "extract_domain",
    "is_same_domain",
]

