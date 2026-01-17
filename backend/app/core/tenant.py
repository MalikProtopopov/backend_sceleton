"""Default tenant utilities for single-tenant mode.

This module provides functions for working with the default tenant
in single-tenant deployments. When single_tenant_mode is enabled,
the system automatically uses the default tenant without requiring
X-Tenant-ID headers.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

# Cache for default tenant ID to avoid repeated database queries
_default_tenant_id: UUID | None = None


async def get_default_tenant(db: AsyncSession):
    """Get the default tenant from the database.
    
    Args:
        db: Database session
        
    Returns:
        Tenant object
        
    Raises:
        RuntimeError: If default tenant is not found
    """
    # Import here to avoid circular imports
    from app.modules.tenants.models import Tenant
    
    stmt = select(Tenant).where(
        Tenant.slug == settings.default_tenant_slug,
        Tenant.deleted_at.is_(None)
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise RuntimeError(
            f"Default tenant '{settings.default_tenant_slug}' not found. "
            "Run 'python -m app.scripts.init_admin' to create it."
        )
    
    return tenant


async def get_default_tenant_id(db: AsyncSession) -> UUID:
    """Get the default tenant ID with caching.
    
    This function caches the tenant ID after the first lookup
    to avoid repeated database queries.
    
    Args:
        db: Database session
        
    Returns:
        UUID of the default tenant
    """
    global _default_tenant_id
    
    if _default_tenant_id is None:
        tenant = await get_default_tenant(db)
        _default_tenant_id = tenant.id
    
    return _default_tenant_id


def clear_tenant_cache() -> None:
    """Clear the cached tenant ID.
    
    Useful for testing or when the default tenant changes.
    """
    global _default_tenant_id
    _default_tenant_id = None


async def validate_tenant_exists(db: AsyncSession, tenant_id: UUID) -> bool:
    """Validate that a tenant exists and is active.
    
    Args:
        db: Database session
        tenant_id: UUID of tenant to validate
        
    Returns:
        True if tenant exists and is active
    """
    # Import here to avoid circular imports
    from app.modules.tenants.models import Tenant
    
    stmt = select(Tenant).where(
        Tenant.id == tenant_id,
        Tenant.is_active.is_(True),
        Tenant.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()
    
    return tenant is not None
