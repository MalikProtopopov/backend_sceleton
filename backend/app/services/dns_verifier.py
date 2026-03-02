"""Backward-compatible re-export. Actual code moved to app.modules.tenants.services."""
from app.modules.tenants.services.dns_verifier import DNSCheckResult, verify_domain_dns  # noqa: F401
