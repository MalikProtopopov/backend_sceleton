"""Base service with common CRUD operations.

Provides reusable patterns for service layer to reduce code duplication.
"""

from datetime import UTC, datetime
from typing import Any, Generic, Sequence, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, joinedload, selectinload
from sqlalchemy.sql import Select

from app.core.base_model import Base, SoftDeleteMixin, TenantMixin
from app.core.exceptions import NotFoundError

# Type variable for models
ModelT = TypeVar("ModelT", bound=Base)


class BaseService(Generic[ModelT]):
    """Base service class with common CRUD operations.
    
    Provides standard patterns for:
    - get_by_id with tenant isolation
    - soft delete
    - pagination
    - list operations
    
    Usage:
        class ArticleService(BaseService[Article]):
            model = Article
            
            def _get_default_options(self) -> list:
                return [
                    selectinload(Article.locales),
                    selectinload(Article.topics),
                ]
            
            async def get_by_id(self, article_id: UUID, tenant_id: UUID) -> Article:
                return await self._get_by_id(article_id, tenant_id)
    """
    
    # Override in subclass
    model: type[ModelT]
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _get_default_options(self) -> list[Any]:
        """Override in subclass to provide default eager loading options.
        
        This method is called at runtime to avoid mapper configuration issues.
        """
        return []
    
    async def _get_by_id(
        self,
        entity_id: UUID,
        tenant_id: UUID,
        *,
        options: list[Any] | None = None,
        include_deleted: bool = False,
    ) -> ModelT:
        """Get entity by ID with tenant isolation.
        
        Args:
            entity_id: Entity UUID
            tenant_id: Tenant UUID for isolation
            options: SQLAlchemy loading options (default: self.default_options)
            include_deleted: If True, include soft-deleted records
            
        Returns:
            Entity instance
            
        Raises:
            NotFoundError: If entity not found
        """
        load_options = options if options is not None else self._get_default_options()
        
        stmt = (
            select(self.model)
            .where(self.model.id == entity_id)
        )
        
        # Add tenant filter if model has tenant_id
        if hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        
        # Add soft delete filter if model has deleted_at
        if hasattr(self.model, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        
        # Add loading options
        if load_options:
            stmt = stmt.options(*load_options)
        
        result = await self.db.execute(stmt)
        entity = result.scalar_one_or_none()
        
        if not entity:
            raise NotFoundError(self.model.__name__, entity_id)
        
        return entity
    
    async def _soft_delete(self, entity_id: UUID, tenant_id: UUID) -> None:
        """Soft delete an entity.
        
        Args:
            entity_id: Entity UUID
            tenant_id: Tenant UUID
            
        Raises:
            NotFoundError: If entity not found
        """
        entity = await self._get_by_id(entity_id, tenant_id, options=[])
        
        if hasattr(entity, "soft_delete"):
            entity.soft_delete()
        elif hasattr(entity, "deleted_at"):
            entity.deleted_at = datetime.now(UTC)
        else:
            raise TypeError(f"{self.model.__name__} does not support soft delete")
        
        await self.db.flush()
    
    async def _paginate(
        self,
        base_query: Select,
        page: int,
        page_size: int,
        *,
        options: list[Any] | None = None,
        order_by: list[Any] | None = None,
    ) -> tuple[list[ModelT], int]:
        """Execute paginated query.
        
        Args:
            base_query: Base select query (filters applied)
            page: Page number (1-indexed)
            page_size: Items per page
            options: SQLAlchemy loading options
            order_by: Order by clauses
            
        Returns:
            Tuple of (items, total_count)
        """
        load_options = options if options is not None else self._get_default_options()
        
        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0
        
        # Build query with options
        stmt = base_query
        if load_options:
            stmt = stmt.options(*load_options)
        
        if order_by:
            stmt = stmt.order_by(*order_by)
        
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        
        return items, total
    
    async def _list_all(
        self,
        tenant_id: UUID,
        *,
        filters: list[Any] | None = None,
        options: list[Any] | None = None,
        order_by: list[Any] | None = None,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        """List all entities without pagination.
        
        Args:
            tenant_id: Tenant UUID
            filters: Additional filter conditions
            options: SQLAlchemy loading options
            order_by: Order by clauses
            include_deleted: Include soft-deleted records
            
        Returns:
            List of entities
        """
        load_options = options if options is not None else self._get_default_options()
        
        stmt = select(self.model)
        
        # Add tenant filter if model has tenant_id
        if hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        
        # Add soft delete filter
        if hasattr(self.model, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        
        # Add additional filters
        if filters:
            for filter_condition in filters:
                stmt = stmt.where(filter_condition)
        
        # Add loading options
        if load_options:
            stmt = stmt.options(*load_options)
        
        # Add ordering
        if order_by:
            stmt = stmt.order_by(*order_by)
        elif hasattr(self.model, "sort_order"):
            stmt = stmt.order_by(self.model.sort_order)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    def _build_base_query(
        self,
        tenant_id: UUID,
        *,
        filters: list[Any] | None = None,
        include_deleted: bool = False,
    ) -> Select:
        """Build base query with tenant and soft-delete filters.
        
        Args:
            tenant_id: Tenant UUID
            filters: Additional filter conditions
            include_deleted: Include soft-deleted records
            
        Returns:
            SQLAlchemy Select query
        """
        stmt = select(self.model)
        
        # Add tenant filter if model has tenant_id
        if hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)
        
        # Add soft delete filter
        if hasattr(self.model, "deleted_at") and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        
        # Add additional filters
        if filters:
            for filter_condition in filters:
                stmt = stmt.where(filter_condition)
        
        return stmt


async def update_many_to_many(
    db: AsyncSession,
    entity: Base,
    relationship_attr: str,
    new_ids: list[UUID],
    link_model: type[Base],
    entity_id_field: str,
    related_id_field: str,
) -> None:
    """Update many-to-many relationship.
    
    Removes existing links and creates new ones.
    
    Args:
        db: Database session
        entity: Parent entity
        relationship_attr: Name of relationship attribute on entity
        new_ids: List of new related entity IDs
        link_model: Link table model class
        entity_id_field: Field name for entity ID in link table
        related_id_field: Field name for related entity ID in link table
        
    Example:
        await update_many_to_many(
            db=self.db,
            entity=employee,
            relationship_attr="practice_areas",
            new_ids=data.practice_area_ids,
            link_model=EmployeePracticeArea,
            entity_id_field="employee_id",
            related_id_field="practice_area_id",
        )
    """
    from uuid import uuid4
    
    # Get existing links
    existing_links = getattr(entity, relationship_attr, [])
    
    # Remove all existing links
    for link in existing_links:
        await db.delete(link)
    
    # Flush deletions to avoid unique constraint violations
    await db.flush()
    
    # Add new links (deduplicated)
    seen_ids: set[UUID] = set()
    for related_id in new_ids:
        if related_id not in seen_ids:
            seen_ids.add(related_id)
            link = link_model(
                id=uuid4(),
                **{entity_id_field: entity.id, related_id_field: related_id}
            )
            db.add(link)
