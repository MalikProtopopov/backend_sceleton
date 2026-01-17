"""Common FastAPI dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    DefaultTenantConfigError,
    InvalidTenantIdError,
    TenantHeaderRequiredError,
    TenantNotFoundError,
)

# Type alias for database dependency
DBSession = Annotated[AsyncSession, Depends(get_db)]


class PaginationParams:
    """Common pagination parameters."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Page number"),
        page_size: int = Query(
            default=20, ge=1, le=100, alias="page_size", description="Items per page"
        ),
    ) -> None:
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size

    @property
    def limit(self) -> int:
        return self.page_size


Pagination = Annotated[PaginationParams, Depends()]


class SortParams:
    """Common sorting parameters."""

    def __init__(
        self,
        sort_by: str = Query(
            default="created_at",
            alias="sortBy",
            description="Field to sort by",
        ),
        sort_order: str = Query(
            default="desc",
            alias="sortOrder",
            pattern="^(asc|desc)$",
            description="Sort order: asc or desc",
        ),
    ) -> None:
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def is_ascending(self) -> bool:
        return self.sort_order == "asc"


Sorting = Annotated[SortParams, Depends()]


class LocaleParams:
    """Locale parameter for public API."""

    def __init__(
        self,
        locale: str = Query(
            default="ru",
            min_length=2,
            max_length=5,
            description="Locale code (e.g., 'ru', 'en')",
        ),
    ) -> None:
        self.locale = locale


Locale = Annotated[LocaleParams, Depends()]


class FilterParams:
    """Common filter parameters for lists."""

    def __init__(
        self,
        search: str | None = Query(
            default=None,
            min_length=1,
            max_length=100,
            description="Search query",
        ),
        is_published: bool | None = Query(
            default=None,
            alias="isPublished",
            description="Filter by published status",
        ),
    ) -> None:
        self.search = search
        self.is_published = is_published


Filtering = Annotated[FilterParams, Depends()]


async def get_public_tenant_id(
    tenant_id: UUID | None = Query(
        default=None,
        description="Tenant ID (optional in single-tenant mode, required in multi-tenant mode)"
    ),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Get tenant_id for public endpoints.
    
    In single-tenant mode:
    - Automatically uses default tenant if not provided
    - Client doesn't need to pass tenant_id parameter
    - If provided, it's ignored and default tenant is used (for security)
    
    In multi-tenant mode:
    - tenant_id is required
    """
    from app.config import settings
    from app.core.tenant import get_default_tenant_id
    
    # In single-tenant mode, always use default tenant (ignore provided tenant_id for security)
    if settings.single_tenant_mode:
        return await get_default_tenant_id(db)
    
    # Multi-tenant mode requires tenant_id
    if tenant_id is None:
        from app.core.exceptions import TenantRequiredError
        raise TenantRequiredError()
    
    return tenant_id


PublicTenantId = Annotated[UUID, Depends(get_public_tenant_id)]


async def get_tenant_from_header(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
) -> UUID:
    """Get tenant_id from X-Tenant-ID header for admin endpoints.
    
    In single-tenant mode (settings.single_tenant_mode=True), the system
    automatically uses the default tenant without requiring X-Tenant-ID header.
    
    In multi-tenant mode, X-Tenant-ID header is required and the tenant
    must exist and be active.
    
    Args:
        x_tenant_id: X-Tenant-ID header value
        db: Database session
        
    Returns:
        UUID of validated tenant
        
    Raises:
        DefaultTenantConfigError: If default tenant is misconfigured (single-tenant mode)
        TenantHeaderRequiredError: If header is missing (multi-tenant mode)
        InvalidTenantIdError: If header value is not a valid UUID
        TenantNotFoundError: If tenant doesn't exist or is inactive
    """
    from app.config import settings
    from app.core.tenant import get_default_tenant_id, validate_tenant_exists
    
    # In single-tenant mode, always use default tenant (ignore X-Tenant-ID header)
    if settings.single_tenant_mode:
        try:
            return await get_default_tenant_id(db)
        except RuntimeError as e:
            raise DefaultTenantConfigError(str(e))
    
    # Multi-tenant mode: require and validate X-Tenant-ID header
    if x_tenant_id:
        try:
            tenant_id = UUID(x_tenant_id)
        except ValueError:
            raise InvalidTenantIdError(x_tenant_id)
        
        # Validate tenant exists and is active
        if not await validate_tenant_exists(db, tenant_id):
            raise TenantNotFoundError(tenant_id)
        
        return tenant_id
    
    # Multi-tenant mode requires X-Tenant-ID header
    raise TenantHeaderRequiredError()


TenantFromHeader = Annotated[UUID, Depends(get_tenant_from_header)]

