"""Unit tests for DocumentService.

Tests the document service with database operations.
Following TEST_RECOMENDATIONS.md structure.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, SlugAlreadyExistsError, VersionConflictError
from app.modules.documents.models import Document, DocumentLocale, DocumentStatus
from app.modules.documents.schemas import (
    DocumentCreate,
    DocumentLocaleCreate,
    DocumentLocaleUpdate,
    DocumentUpdate,
    DocumentStatus as SchemaDocumentStatus,
)
from app.modules.documents.service import DocumentService


class TestDocumentServiceCreate:
    """Tests for document creation."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> DocumentService:
        """Create service instance."""
        return DocumentService(db_session)

    @pytest_asyncio.fixture
    async def create_data(self) -> DocumentCreate:
        """Create valid document data."""
        return DocumentCreate(
            status=SchemaDocumentStatus.DRAFT,
            document_version="1.0",
            document_date=date(2026, 1, 15),
            sort_order=0,
            locales=[
                DocumentLocaleCreate(
                    locale="en",
                    title="Privacy Policy",
                    slug="privacy-policy",
                    excerpt="Our privacy policy",
                    full_description="<p>Full privacy policy content</p>",
                    meta_title="Privacy Policy | Company",
                    meta_description="Learn about our privacy practices",
                ),
                DocumentLocaleCreate(
                    locale="ru",
                    title="Политика конфиденциальности",
                    slug="politika-konfidencialnosti",
                    excerpt="Наша политика конфиденциальности",
                    full_description="<p>Полный текст политики</p>",
                    meta_title="Политика конфиденциальности",
                    meta_description="Узнайте о наших практиках",
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_create_document_success(
        self,
        service: DocumentService,
        create_data: DocumentCreate,
        test_tenant,
    ):
        """Test successful document creation."""
        document = await service.create(test_tenant.id, create_data)

        assert document.id is not None
        assert document.tenant_id == test_tenant.id
        assert document.status == DocumentStatus.DRAFT.value
        assert document.document_version == "1.0"
        assert document.document_date == date(2026, 1, 15)
        assert len(document.locales) == 2

    @pytest.mark.asyncio
    async def test_create_document_locales_saved(
        self,
        service: DocumentService,
        create_data: DocumentCreate,
        test_tenant,
    ):
        """Test that locales are properly saved."""
        document = await service.create(test_tenant.id, create_data)

        en_locale = next((l for l in document.locales if l.locale == "en"), None)
        ru_locale = next((l for l in document.locales if l.locale == "ru"), None)

        assert en_locale is not None
        assert en_locale.title == "Privacy Policy"
        assert en_locale.slug == "privacy-policy"
        assert en_locale.excerpt == "Our privacy policy"
        assert "<p>Full privacy policy content</p>" in en_locale.full_description

        assert ru_locale is not None
        assert ru_locale.title == "Политика конфиденциальности"
        assert ru_locale.slug == "politika-konfidencialnosti"

    @pytest.mark.asyncio
    async def test_create_document_without_optional_fields(
        self,
        service: DocumentService,
        test_tenant,
    ):
        """Test creation without optional fields."""
        data = DocumentCreate(
            locales=[
                DocumentLocaleCreate(
                    locale="en",
                    title="Simple Document",
                    slug="simple-document",
                ),
            ],
        )

        document = await service.create(test_tenant.id, data)

        assert document.document_version is None
        assert document.document_date is None
        assert document.file_url is None


class TestDocumentServiceGetById:
    """Tests for getting document by ID."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> DocumentService:
        """Create service instance."""
        return DocumentService(db_session)

    @pytest_asyncio.fixture
    async def existing_document(
        self,
        db_session: AsyncSession,
        test_tenant,
    ) -> Document:
        """Create a document for testing."""
        document = Document(
            tenant_id=test_tenant.id,
            status=DocumentStatus.PUBLISHED.value,
            document_version="2.0",
            document_date=date(2026, 1, 10),
            published_at=datetime.utcnow(),
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="Test Document",
            slug="test-document",
            excerpt="Test excerpt",
            full_description="<p>Test content</p>",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(document, ["locales"])

        return document

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self,
        service: DocumentService,
        existing_document: Document,
        test_tenant,
    ):
        """Test successful retrieval by ID."""
        document = await service.get_by_id(existing_document.id, test_tenant.id)

        assert document.id == existing_document.id
        assert document.document_version == "2.0"
        assert len(document.locales) == 1

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        service: DocumentService,
        test_tenant,
    ):
        """Test NotFoundError for non-existent document."""
        with pytest.raises(NotFoundError) as exc_info:
            await service.get_by_id(uuid4(), test_tenant.id)

        assert "Document" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_by_id_wrong_tenant(
        self,
        service: DocumentService,
        existing_document: Document,
    ):
        """Test NotFoundError when accessing from wrong tenant."""
        wrong_tenant_id = uuid4()

        with pytest.raises(NotFoundError):
            await service.get_by_id(existing_document.id, wrong_tenant_id)


class TestDocumentServiceGetBySlug:
    """Tests for getting document by slug."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> DocumentService:
        """Create service instance."""
        return DocumentService(db_session)

    @pytest_asyncio.fixture
    async def published_document(
        self,
        db_session: AsyncSession,
        test_tenant,
    ) -> Document:
        """Create a published document."""
        document = Document(
            tenant_id=test_tenant.id,
            status=DocumentStatus.PUBLISHED.value,
            published_at=datetime.utcnow(),
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="Terms of Service",
            slug="terms-of-service",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(document, ["locales"])

        return document

    @pytest.mark.asyncio
    async def test_get_by_slug_success(
        self,
        service: DocumentService,
        published_document: Document,
        test_tenant,
    ):
        """Test successful retrieval by slug."""
        document = await service.get_by_slug(
            "terms-of-service", "en", test_tenant.id
        )

        assert document.id == published_document.id

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(
        self,
        service: DocumentService,
        test_tenant,
    ):
        """Test NotFoundError for non-existent slug."""
        with pytest.raises(NotFoundError):
            await service.get_by_slug("non-existent", "en", test_tenant.id)

    @pytest.mark.asyncio
    async def test_get_by_slug_draft_not_found(
        self,
        db_session: AsyncSession,
        service: DocumentService,
        test_tenant,
    ):
        """Test that draft documents are not found by slug."""
        # Create draft document
        document = Document(
            tenant_id=test_tenant.id,
            status=DocumentStatus.DRAFT.value,
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="Draft Doc",
            slug="draft-doc",
        )
        db_session.add(locale)
        await db_session.flush()

        with pytest.raises(NotFoundError):
            await service.get_by_slug("draft-doc", "en", test_tenant.id)


class TestDocumentServiceUpdate:
    """Tests for document update."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> DocumentService:
        """Create service instance."""
        return DocumentService(db_session)

    @pytest_asyncio.fixture
    async def existing_document(
        self,
        db_session: AsyncSession,
        test_tenant,
    ) -> Document:
        """Create a document for testing."""
        document = Document(
            tenant_id=test_tenant.id,
            status=DocumentStatus.DRAFT.value,
            document_version="1.0",
            version=1,
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="Original Title",
            slug="original-slug",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(document, ["locales"])

        return document

    @pytest.mark.asyncio
    async def test_update_document_fields(
        self,
        service: DocumentService,
        existing_document: Document,
        test_tenant,
    ):
        """Test updating document fields."""
        update_data = DocumentUpdate(
            document_version="2.0",
            document_date=date(2026, 2, 1),
            version=1,
        )

        updated = await service.update(
            existing_document.id, test_tenant.id, update_data
        )

        assert updated.document_version == "2.0"
        assert updated.document_date == date(2026, 2, 1)

    @pytest.mark.asyncio
    async def test_update_locale_content(
        self,
        service: DocumentService,
        existing_document: Document,
        test_tenant,
    ):
        """Test updating locale content."""
        update_data = DocumentUpdate(
            locales=[
                DocumentLocaleUpdate(
                    locale="en",
                    title="Updated Title",
                    excerpt="New excerpt",
                ),
            ],
            version=1,
        )

        updated = await service.update(
            existing_document.id, test_tenant.id, update_data
        )

        en_locale = next((l for l in updated.locales if l.locale == "en"), None)
        assert en_locale.title == "Updated Title"
        assert en_locale.excerpt == "New excerpt"

    @pytest.mark.asyncio
    async def test_update_version_conflict(
        self,
        service: DocumentService,
        existing_document: Document,
        test_tenant,
    ):
        """Test version conflict error."""
        update_data = DocumentUpdate(
            document_version="3.0",
            version=999,  # Wrong version
        )

        with pytest.raises(VersionConflictError):
            await service.update(
                existing_document.id, test_tenant.id, update_data
            )


class TestDocumentServicePublish:
    """Tests for publish/unpublish operations."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> DocumentService:
        """Create service instance."""
        return DocumentService(db_session)

    @pytest_asyncio.fixture
    async def draft_document(
        self,
        db_session: AsyncSession,
        test_tenant,
    ) -> Document:
        """Create a draft document."""
        document = Document(
            tenant_id=test_tenant.id,
            status=DocumentStatus.DRAFT.value,
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="Draft Document",
            slug="draft-document",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(document, ["locales"])

        return document

    @pytest.mark.asyncio
    async def test_publish_document(
        self,
        service: DocumentService,
        draft_document: Document,
        test_tenant,
    ):
        """Test publishing a document."""
        published = await service.publish(draft_document.id, test_tenant.id)

        assert published.status == DocumentStatus.PUBLISHED.value
        assert published.published_at is not None

    @pytest.mark.asyncio
    async def test_unpublish_document(
        self,
        db_session: AsyncSession,
        service: DocumentService,
        test_tenant,
    ):
        """Test unpublishing a document."""
        # Create published document
        document = Document(
            tenant_id=test_tenant.id,
            status=DocumentStatus.PUBLISHED.value,
            published_at=datetime.utcnow(),
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="Published Doc",
            slug="published-doc",
        )
        db_session.add(locale)
        await db_session.flush()

        unpublished = await service.unpublish(document.id, test_tenant.id)

        assert unpublished.status == DocumentStatus.DRAFT.value


class TestDocumentServiceSoftDelete:
    """Tests for soft delete."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> DocumentService:
        """Create service instance."""
        return DocumentService(db_session)

    @pytest_asyncio.fixture
    async def existing_document(
        self,
        db_session: AsyncSession,
        test_tenant,
    ) -> Document:
        """Create a document for testing."""
        document = Document(
            tenant_id=test_tenant.id,
            status=DocumentStatus.DRAFT.value,
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="To Delete",
            slug="to-delete",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(document, ["locales"])

        return document

    @pytest.mark.asyncio
    async def test_soft_delete_document(
        self,
        service: DocumentService,
        existing_document: Document,
        test_tenant,
    ):
        """Test soft deleting a document."""
        await service.soft_delete(existing_document.id, test_tenant.id)

        # Should not be found after deletion
        with pytest.raises(NotFoundError):
            await service.get_by_id(existing_document.id, test_tenant.id)


class TestDocumentServiceList:
    """Tests for listing documents."""

    @pytest_asyncio.fixture
    async def service(self, db_session: AsyncSession) -> DocumentService:
        """Create service instance."""
        return DocumentService(db_session)

    @pytest_asyncio.fixture
    async def documents(
        self,
        db_session: AsyncSession,
        test_tenant,
    ) -> list[Document]:
        """Create multiple documents for testing."""
        docs = []
        for i in range(5):
            status = DocumentStatus.PUBLISHED.value if i < 3 else DocumentStatus.DRAFT.value
            document = Document(
                tenant_id=test_tenant.id,
                status=status,
                document_version=f"1.{i}",
                document_date=date(2026, 1, 10 + i),
                sort_order=i,
                published_at=datetime.utcnow() if status == DocumentStatus.PUBLISHED.value else None,
            )
            db_session.add(document)
            await db_session.flush()

            locale = DocumentLocale(
                document_id=document.id,
                locale="en",
                title=f"Document {i}",
                slug=f"document-{i}",
            )
            db_session.add(locale)
            docs.append(document)

        await db_session.flush()
        return docs

    @pytest.mark.asyncio
    async def test_list_documents_all(
        self,
        service: DocumentService,
        documents: list[Document],
        test_tenant,
    ):
        """Test listing all documents."""
        result, total = await service.list_documents(test_tenant.id)

        assert total == 5
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_list_documents_by_status(
        self,
        service: DocumentService,
        documents: list[Document],
        test_tenant,
    ):
        """Test filtering by status."""
        result, total = await service.list_documents(
            test_tenant.id, status="published"
        )

        assert total == 3
        assert all(d.status == "published" for d in result)

    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self,
        service: DocumentService,
        documents: list[Document],
        test_tenant,
    ):
        """Test pagination."""
        result, total = await service.list_documents(
            test_tenant.id, page=1, page_size=2
        )

        assert total == 5
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_published_only(
        self,
        service: DocumentService,
        documents: list[Document],
        test_tenant,
    ):
        """Test listing published documents only."""
        result, total = await service.list_published(
            test_tenant.id, locale="en"
        )

        assert total == 3
        assert all(d.status == "published" for d in result)

