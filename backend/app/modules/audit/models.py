"""Audit log database models.

Note: AuditLog model is defined in app.modules.auth.models to avoid duplication.
This module only contains service and router logic.
"""

# Import AuditLog from auth module to use the existing model
from app.modules.auth.models import AuditLog

__all__ = ["AuditLog"]

