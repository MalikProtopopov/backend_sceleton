"""Pagination utilities for database queries.

Provides reusable pagination pattern to reduce code duplication across services.
"""

from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.base_model import Base

# Type variable for models
T = TypeVar("T", bound=Base)


class PaginatedResult(Generic[T]):
    """Container for paginated query results.
    
    Attributes:
        items: List of items for current page
        total: Total count of items matching query
        page: Current page number (1-indexed)
        page_size: Number of items per page
        pages: Total number of pages
    """
    
    def __init__(
        self,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> None:
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
    
    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there is a next page."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there is a previous page."""
        return self.page > 1
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": self.pages,
        }


async def paginate_query(
    db: AsyncSession,
    base_query: Select,
    page: int,
    page_size: int,
    *,
    options: list[Any] | None = None,
    order_by: list[Any] | None = None,
    unique: bool = False,
) -> tuple[list[Any], int]:
    """Execute a paginated query.
    
    Standard pagination pattern used across all services.
    
    Args:
        db: Database session
        base_query: Base SELECT query with filters applied
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100 enforced)
        options: SQLAlchemy loading options (selectinload, joinedload, etc.)
        order_by: List of order_by clauses
        unique: If True, use scalars().unique() for deduplication (use with joins)
        
    Returns:
        Tuple of (items_list, total_count)
        
    Example:
        # In service method:
        base_query = (
            select(Article)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
        )
        
        items, total = await paginate_query(
            self.db,
            base_query,
            page=page,
            page_size=page_size,
            options=[selectinload(Article.locales)],
            order_by=[Article.created_at.desc()],
        )
    """
    # Enforce max page size
    page_size = min(page_size, 100)
    page = max(page, 1)
    
    # Count total
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Build final query
    stmt = base_query
    
    if options:
        stmt = stmt.options(*options)
    
    if order_by:
        stmt = stmt.order_by(*order_by)
    
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    
    # Execute
    result = await db.execute(stmt)
    
    if unique:
        items = list(result.scalars().unique().all())
    else:
        items = list(result.scalars().all())
    
    return items, total


async def paginate(
    db: AsyncSession,
    base_query: Select,
    page: int,
    page_size: int,
    *,
    options: list[Any] | None = None,
    order_by: list[Any] | None = None,
    unique: bool = False,
) -> PaginatedResult:
    """Execute paginated query and return PaginatedResult.
    
    Same as paginate_query but returns a PaginatedResult object.
    
    Args:
        db: Database session
        base_query: Base SELECT query with filters applied
        page: Page number (1-indexed)
        page_size: Number of items per page
        options: SQLAlchemy loading options
        order_by: List of order_by clauses
        unique: If True, use scalars().unique() for deduplication
        
    Returns:
        PaginatedResult with items, total, page info
    """
    items, total = await paginate_query(
        db,
        base_query,
        page,
        page_size,
        options=options,
        order_by=order_by,
        unique=unique,
    )
    
    return PaginatedResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
