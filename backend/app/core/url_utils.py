"""Backward-compatible re-export. Actual code moved to app.modules.seo.utils."""
from app.modules.seo.utils import (  # noqa: F401
    build_sitemap_url,
    extract_domain,
    is_same_domain,
    normalize_path,
    normalize_url,
    validate_base_url,
)
