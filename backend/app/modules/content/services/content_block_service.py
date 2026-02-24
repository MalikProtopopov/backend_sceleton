"""Content module - content block service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import transactional
from app.core.exceptions import NotFoundError
from app.modules.content.models import ContentBlock
from app.modules.content.schemas import (
    ContentBlockCreate,
    ContentBlockUpdate,
)


class ContentBlockService:
    """Service for managing content blocks.
    
    Provides CRUD operations for flexible content blocks that can be attached
    to articles, cases, and services. Supports different block types:
    - text: HTML content
    - image: Single image with metadata
    - video: Embedded video (YouTube, RuTube)
    - gallery: Image slider/gallery
    - link: External link (website, TG bot)
    - result: Result block with mixed content
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_blocks(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        locale: str | None = None,
    ) -> list[ContentBlock]:
        """List content blocks for an entity.
        
        Args:
            entity_type: Type of entity (article, case, service)
            entity_id: ID of the entity
            tenant_id: Tenant ID
            locale: Optional locale filter
            
        Returns:
            List of content blocks ordered by sort_order
        """
        stmt = (
            select(ContentBlock)
            .where(ContentBlock.tenant_id == tenant_id)
            .where(ContentBlock.entity_type == entity_type)
            .where(ContentBlock.entity_id == entity_id)
        )
        
        if locale:
            stmt = stmt.where(ContentBlock.locale == locale)
        
        stmt = stmt.order_by(ContentBlock.locale, ContentBlock.sort_order)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_block(
        self,
        block_id: UUID,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
    ) -> ContentBlock:
        """Get a content block by ID.
        
        Args:
            block_id: Block ID
            entity_type: Type of entity
            entity_id: ID of the entity
            tenant_id: Tenant ID
            
        Returns:
            Content block
            
        Raises:
            NotFoundError: If block not found
        """
        stmt = select(ContentBlock).where(
            ContentBlock.id == block_id,
            ContentBlock.tenant_id == tenant_id,
            ContentBlock.entity_type == entity_type,
            ContentBlock.entity_id == entity_id,
        )
        result = await self.db.execute(stmt)
        block = result.scalar_one_or_none()
        
        if not block:
            raise NotFoundError("ContentBlock", block_id)
        
        return block

    @transactional
    async def add_block(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        data: ContentBlockCreate,
    ) -> ContentBlock:
        """Add a content block to an entity.
        
        Args:
            entity_type: Type of entity (article, case, service)
            entity_id: ID of the entity
            tenant_id: Tenant ID
            data: Block data
            
        Returns:
            Created content block
        """
        block = ContentBlock(
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            locale=data.locale,
            block_type=data.block_type.value,
            sort_order=data.sort_order,
            title=data.title,
            content=data.content,
            media_url=data.media_url,
            thumbnail_url=data.thumbnail_url,
            link_url=data.link_url,
            link_label=data.link_label,
            device_type=data.device_type.value if data.device_type else None,
            block_metadata=data.block_metadata,
        )
        self.db.add(block)
        await self.db.flush()
        await self.db.refresh(block)
        return block

    @transactional
    async def update_block(
        self,
        block_id: UUID,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        data: ContentBlockUpdate,
    ) -> ContentBlock:
        """Update a content block.
        
        Args:
            block_id: Block ID
            entity_type: Type of entity
            entity_id: ID of the entity
            tenant_id: Tenant ID
            data: Update data
            
        Returns:
            Updated content block
        """
        block = await self.get_block(block_id, entity_type, entity_id, tenant_id)
        
        # Update fields that are provided
        if data.locale is not None:
            block.locale = data.locale
        if data.block_type is not None:
            block.block_type = data.block_type.value
        if data.sort_order is not None:
            block.sort_order = data.sort_order
        if data.title is not None:
            block.title = data.title
        if data.content is not None:
            block.content = data.content
        if data.media_url is not None:
            block.media_url = data.media_url
        if data.thumbnail_url is not None:
            block.thumbnail_url = data.thumbnail_url
        if data.link_url is not None:
            block.link_url = data.link_url
        if data.link_label is not None:
            block.link_label = data.link_label
        if data.device_type is not None:
            block.device_type = data.device_type.value
        if data.block_metadata is not None:
            block.block_metadata = data.block_metadata
        
        await self.db.flush()
        await self.db.refresh(block)
        return block

    @transactional
    async def delete_block(
        self,
        block_id: UUID,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Delete a content block.
        
        Args:
            block_id: Block ID
            entity_type: Type of entity
            entity_id: ID of the entity
            tenant_id: Tenant ID
        """
        block = await self.get_block(block_id, entity_type, entity_id, tenant_id)
        await self.db.delete(block)
        await self.db.flush()

    @transactional
    async def reorder_blocks(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        locale: str,
        block_ids: list[UUID],
    ) -> list[ContentBlock]:
        """Reorder content blocks.
        
        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            tenant_id: Tenant ID
            locale: Locale of blocks to reorder
            block_ids: Ordered list of block IDs
            
        Returns:
            Reordered list of content blocks
        """
        # Fetch all blocks for this entity/locale
        blocks = await self.list_blocks(entity_type, entity_id, tenant_id, locale)
        blocks_by_id = {block.id: block for block in blocks}
        
        # Update sort_order based on provided order
        for index, block_id in enumerate(block_ids):
            if block_id in blocks_by_id:
                blocks_by_id[block_id].sort_order = index
        
        await self.db.flush()
        
        # Return reordered list
        return await self.list_blocks(entity_type, entity_id, tenant_id, locale)
