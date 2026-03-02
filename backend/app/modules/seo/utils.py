"""URL utilities for SEO path normalization and validation."""

import re
from urllib.parse import urlparse, urlunparse


def normalize_path(path: str) -> str:
    """Normalize a URL path to canonical form.
    
    Canonical path rules:
    - Always starts with /
    - No double slashes (// -> /)
    - No . or .. segments resolved
    - No query strings or fragments
    - No trailing slash (except for root /)
    - Lowercase
    
    Args:
        path: The URL path to normalize
        
    Returns:
        Normalized path string
        
    Examples:
        >>> normalize_path("/Services/")
        "/services"
        >>> normalize_path("//foo//bar")
        "/foo/bar"
        >>> normalize_path("/path?query=1#hash")
        "/path"
        >>> normalize_path("/foo/../bar")
        "/bar"
        >>> normalize_path("")
        "/"
    """
    if not path:
        return "/"
    
    # Remove query string and fragment
    if "?" in path:
        path = path.split("?")[0]
    if "#" in path:
        path = path.split("#")[0]
    
    # Ensure leading slash
    if not path.startswith("/"):
        path = "/" + path
    
    # Collapse multiple slashes
    path = re.sub(r"/+", "/", path)
    
    # Resolve . and .. segments
    segments = path.split("/")
    resolved: list[str] = []
    
    for segment in segments:
        if segment == "..":
            if resolved and resolved[-1] != "":
                resolved.pop()
        elif segment != "." and segment != "":
            resolved.append(segment)
    
    # Rebuild path
    path = "/" + "/".join(resolved)
    
    # Remove trailing slash (except for root)
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    
    # Lowercase
    path = path.lower()
    
    return path


def normalize_url(url: str) -> str:
    """Normalize a full URL.
    
    Args:
        url: Full URL to normalize
        
    Returns:
        Normalized URL with canonical path
    """
    parsed = urlparse(url)
    normalized_path = normalize_path(parsed.path)
    
    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        normalized_path,
        "",  # params
        "",  # query (removed)
        "",  # fragment (removed)
    ))


def validate_base_url(base_url: str, allowed_domains: list[str] | None = None) -> tuple[bool, str | None]:
    """Validate a base URL against allowed domains.
    
    Args:
        base_url: The base URL to validate
        allowed_domains: List of allowed domain patterns (e.g., ["mediann.dev", "*.mediann.dev"])
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not base_url:
        return False, "base_url is required"
    
    try:
        parsed = urlparse(base_url)
    except Exception:
        return False, "Invalid URL format"
    
    if not parsed.scheme:
        return False, "URL must include scheme (http/https)"
    
    if parsed.scheme not in ("http", "https"):
        return False, "URL scheme must be http or https"
    
    if not parsed.netloc:
        return False, "URL must include domain"
    
    # If no allowed domains specified, accept any
    if not allowed_domains:
        return True, None
    
    domain = parsed.netloc.lower()
    # Remove port if present
    if ":" in domain:
        domain = domain.split(":")[0]
    
    for allowed in allowed_domains:
        allowed = allowed.lower()
        
        # Wildcard subdomain matching
        if allowed.startswith("*."):
            suffix = allowed[2:]  # Remove *.
            if domain == suffix or domain.endswith("." + suffix):
                return True, None
        elif domain == allowed:
            return True, None
    
    return False, f"Domain '{domain}' not in allowed list"


def build_sitemap_url(base_url: str, path: str) -> str:
    """Build a full URL for sitemap from base URL and path.
    
    Handles trailing slash and path joining correctly.
    
    Args:
        base_url: Base URL (e.g., "https://mediann.dev")
        path: URL path (e.g., "/services/web-dev")
        
    Returns:
        Full URL string
    """
    # Normalize the path
    path = normalize_path(path)
    
    # Remove trailing slash from base_url
    base_url = base_url.rstrip("/")
    
    # Path already has leading slash from normalize_path
    return f"{base_url}{path}"


def extract_domain(url: str) -> str | None:
    """Extract domain from URL.
    
    Args:
        url: Full URL
        
    Returns:
        Domain without port, or None if invalid
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain if domain else None
    except Exception:
        return None


def is_same_domain(url1: str, url2: str) -> bool:
    """Check if two URLs have the same domain.
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        True if domains match
    """
    domain1 = extract_domain(url1)
    domain2 = extract_domain(url2)
    
    if not domain1 or not domain2:
        return False
    
    return domain1 == domain2
