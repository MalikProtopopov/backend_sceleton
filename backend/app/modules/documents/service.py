"""Documents module service layer."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import NotFoundError, VersionConflictError
from app.core.locale_helpers import check_slug_unique
from app.modules.documents.models import (
    Document,
    DocumentLocale,
    DocumentStatus,
)
from app.modules.documents.schemas import (
    DocumentCreate,
    DocumentUpdate,
)


class DocumentService:
    """Service for managing documents."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, document_id: UUID, tenant_id: UUID) -> Document:
        """Get document by ID."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
            .options(selectinload(Document.locales))
        )
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundError("Document", document_id)

        return document

    async def get_by_slug(self, slug: str, locale: str, tenant_id: UUID) -> Document:
        """Get published document by slug."""
        stmt = (
            select(Document)
            .join(DocumentLocale)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
            .where(Document.status == DocumentStatus.PUBLISHED.value)
            .where(DocumentLocale.locale == locale)
            .where(DocumentLocale.slug == slug)
            .options(selectinload(Document.locales))
        )
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise NotFoundError("Document", slug)

        return document

    async def list_documents(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        search: str | None = None,
        document_date_from: date | None = None,
        document_date_to: date | None = None,
        sort_by: str = "created_at",
        sort_direction: str = "desc",
    ) -> tuple[list[Document], int]:
        """List documents with pagination and filters."""
        base_query = (
            select(Document)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
        )

        if status:
            base_query = base_query.where(Document.status == status)

        if document_date_from:
            base_query = base_query.where(Document.document_date >= document_date_from)

        if document_date_to:
            base_query = base_query.where(Document.document_date <= document_date_to)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.outerjoin(DocumentLocale).where(
                DocumentLocale.title.ilike(search_pattern)
            )

        # Count total
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Sort
        sort_column = getattr(Document, sort_by, Document.created_at)
        if sort_direction == "asc":
            base_query = base_query.order_by(sort_column.asc())
        else:
            base_query = base_query.order_by(sort_column.desc())

        # Paginate
        stmt = (
            base_query
            .options(selectinload(Document.locales))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        documents = list(result.scalars().unique().all())

        return documents, total

    async def list_published(
        self,
        tenant_id: UUID,
        locale: str,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        document_date_from: date | None = None,
        document_date_to: date | None = None,
    ) -> tuple[list[Document], int]:
        """List published documents for public display."""
        # Filter by locale at database level to ensure correct pagination
        base_query = (
            select(Document)
            .join(DocumentLocale, Document.id == DocumentLocale.document_id)
            .where(Document.tenant_id == tenant_id)
            .where(Document.deleted_at.is_(None))
            .where(Document.status == DocumentStatus.PUBLISHED.value)
            .where(DocumentLocale.locale == locale)
        )

        if document_date_from:
            base_query = base_query.where(Document.document_date >= document_date_from)

        if document_date_to:
            base_query = base_query.where(Document.document_date <= document_date_to)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(DocumentLocale.title.ilike(search_pattern))

        # Count total - reflects items with requested locale
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Fetch with pagination
        stmt = (
            base_query
            .options(selectinload(Document.locales))
            .order_by(Document.sort_order, Document.document_date.desc().nullslast())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        documents = list(result.scalars().unique().all())

        return documents, total

    @transactional
    async def create(self, tenant_id: UUID, data: DocumentCreate) -> Document:
        """Create a new document."""
        # Check slug uniqueness for all locales
        for locale_data in data.locales:
            await check_slug_unique(
                self.db, DocumentLocale, Document, "document_id",
                locale_data.slug, locale_data.locale, tenant_id
            )

        document = Document(
            tenant_id=tenant_id,
            status=data.status.value,
            document_version=data.document_version,
            document_date=data.document_date,
            sort_order=data.sort_order,
        )
        self.db.add(document)
        await self.db.flush()

        for locale_data in data.locales:
            locale = DocumentLocale(
                document_id=document.id,
                locale=locale_data.locale,
                title=locale_data.title,
                slug=locale_data.slug,
                excerpt=locale_data.excerpt,
                full_description=locale_data.full_description,
                meta_title=locale_data.meta_title,
                meta_description=locale_data.meta_description,
            )
            self.db.add(locale)

        await self.db.flush()
        await self.db.refresh(document, ["locales"])

        return document

    @transactional
    async def update(
        self, 
        document_id: UUID, 
        tenant_id: UUID, 
        data: DocumentUpdate
    ) -> Document:
        """Update a document."""
        document = await self.get_by_id(document_id, tenant_id)

        if document.version != data.version:
            raise VersionConflictError("Document", document.version, data.version)

        # Update main fields
        if data.status is not None:
            document.status = data.status.value
        if data.document_version is not None:
            document.document_version = data.document_version
        if data.document_date is not None:
            document.document_date = data.document_date
        if data.sort_order is not None:
            document.sort_order = data.sort_order

        # Update locales if provided
        if data.locales is not None:
            for locale_data in data.locales:
                # Check slug uniqueness
                if locale_data.slug:
                    await check_slug_unique(
                        self.db, DocumentLocale, Document, "document_id",
                        locale_data.slug, locale_data.locale, tenant_id,
                        exclude_parent_id=document_id
                    )

                # Find existing locale or create new
                existing_locale = next(
                    (l for l in document.locales if l.locale == locale_data.locale),
                    None
                )

                if existing_locale:
                    # Update existing locale
                    if locale_data.title is not None:
                        existing_locale.title = locale_data.title
                    if locale_data.slug is not None:
                        existing_locale.slug = locale_data.slug
                    if locale_data.excerpt is not None:
                        existing_locale.excerpt = locale_data.excerpt
                    if locale_data.full_description is not None:
                        existing_locale.full_description = locale_data.full_description
                    if locale_data.meta_title is not None:
                        existing_locale.meta_title = locale_data.meta_title
                    if locale_data.meta_description is not None:
                        existing_locale.meta_description = locale_data.meta_description
                else:
                    # Create new locale
                    new_locale = DocumentLocale(
                        document_id=document.id,
                        locale=locale_data.locale,
                        title=locale_data.title or "",
                        slug=locale_data.slug or "",
                        excerpt=locale_data.excerpt,
                        full_description=locale_data.full_description,
                        meta_title=locale_data.meta_title,
                        meta_description=locale_data.meta_description,
                    )
                    self.db.add(new_locale)

        await self.db.flush()
        await self.db.refresh(document, ["locales"])

        return document

    @transactional
    async def soft_delete(self, document_id: UUID, tenant_id: UUID) -> None:
        """Soft delete a document."""
        document = await self.get_by_id(document_id, tenant_id)
        document.soft_delete()
        await self.db.flush()

    @transactional
    async def publish(self, document_id: UUID, tenant_id: UUID) -> Document:
        """Publish a document."""
        document = await self.get_by_id(document_id, tenant_id)
        document.publish()
        await self.db.flush()
        await self.db.refresh(document, ["locales"])
        return document

    @transactional
    async def unpublish(self, document_id: UUID, tenant_id: UUID) -> Document:
        """Unpublish a document (move to draft)."""
        document = await self.get_by_id(document_id, tenant_id)
        document.unpublish()
        await self.db.flush()
        await self.db.refresh(document, ["locales"])
        return document

