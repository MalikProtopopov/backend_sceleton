"""Audit log module for tracking changes."""

# Import AuditLog from auth module (model is defined there)
from app.modules.auth.models import AuditLog
from app.modules.audit.router import router

__all__ = ["router", "AuditLog"]

