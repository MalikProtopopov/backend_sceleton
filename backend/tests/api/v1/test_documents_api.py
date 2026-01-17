"""API integration tests for documents endpoints.

Tests the documents API endpoints with full HTTP stack.
Following TEST_RECOMENDATIONS.md structure.
"""

from datetime import date, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.models import Document, DocumentLocale, DocumentStatus


class TestPublicDocumentsAPI:
    """Tests for public documents endpoints."""

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
            document_version="1.0",
            document_date=date(2026, 1, 15),
            published_at=datetime.utcnow(),
        )
        db_session.add(document)
        await db_session.flush()

        locale = DocumentLocale(
            document_id=document.id,
            locale="en",
            title="Privacy Policy",
            slug="privacy-policy",
            excerpt="Our privacy commitment",
            full_description="<p>Full privacy policy text</p>",
            meta_title="Privacy Policy | Company",
            meta_description="Learn about our privacy practices",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(document, ["locales"])

        return document

    @pytest.mark.asyncio
    async def test_list_public_documents(
        self,
        client: AsyncClient,
        published_document: Document,
        test_tenant,
    ):
        """Test listing public documents."""
        response = await client.get(
            "/api/v1/public/documents",
            params={
                "tenant_id": str(test_tenant.id),
                "locale": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

        # Check first item
        item = next(
            (i for i in data["items"] if i["slug"] == "privacy-policy"),
            None
        )
        assert item is not None
        assert item["title"] == "Privacy Policy"
        assert item["excerpt"] == "Our privacy commitment"
        # full_description should not be in list
        assert item["full_description"] is None

    @pytest.mark.asyncio
    async def test_get_public_document_by_slug(
        self,
        client: AsyncClient,
        published_document: Document,
        test_tenant,
    ):
        """Test getting public document by slug."""
        response = await client.get(
            "/api/v1/public/documents/privacy-policy",
            params={
                "tenant_id": str(test_tenant.id),
                "locale": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Privacy Policy"
        assert data["slug"] == "privacy-policy"
        assert data["document_version"] == "1.0"
        # full_description SHOULD be in detail view
        assert "<p>Full privacy policy text</p>" in data["full_description"]

    @pytest.mark.asyncio
    async def test_get_public_document_not_found(
        self,
        client: AsyncClient,
        test_tenant,
    ):
        """Test 404 for non-existent document."""
        response = await client.get(
            "/api/v1/public/documents/non-existent",
            params={
                "tenant_id": str(test_tenant.id),
                "locale": "en",
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_public_documents_search(
        self,
        client: AsyncClient,
        published_document: Document,
        test_tenant,
    ):
        """Test searching public documents."""
        response = await client.get(
            "/api/v1/public/documents",
            params={
                "tenant_id": str(test_tenant.id),
                "locale": "en",
                "search": "Privacy",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestAdminDocumentsAPI:
    """Tests for admin documents endpoints."""

    @pytest_asyncio.fixture
    async def existing_document(
        self,
        db_session: AsyncSession,
        test_tenant,
    ) -> Document:
        """Create an existing document for tests."""
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
            title="Existing Document",
            slug="existing-document",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(document, ["locales"])

        return document

    @pytest.mark.asyncio
    async def test_list_admin_documents(
        self,
        superuser_client: AsyncClient,
        existing_document: Document,
    ):
        """Test listing admin documents."""
        response = await superuser_client.get("/api/v1/admin/documents")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_document(
        self,
        superuser_client: AsyncClient,
    ):
        """Test creating a document."""
        create_data = {
            "status": "draft",
            "document_version": "1.0",
            "document_date": "2026-01-15",
            "sort_order": 0,
            "locales": [
                {
                    "locale": "en",
                    "title": "New Document",
                    "slug": f"new-document-{uuid4().hex[:8]}",
                    "excerpt": "A new document",
                    "full_description": "<p>Document content</p>",
                    "meta_title": "New Document | Company",
                    "meta_description": "New document description",
                }
            ],
        }

        response = await superuser_client.post(
            "/api/v1/admin/documents",
            json=create_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["document_version"] == "1.0"
        assert len(data["locales"]) == 1
        assert data["locales"][0]["title"] == "New Document"

    @pytest.mark.asyncio
    async def test_get_admin_document(
        self,
        superuser_client: AsyncClient,
        existing_document: Document,
    ):
        """Test getting a document by ID."""
        response = await superuser_client.get(
            f"/api/v1/admin/documents/{existing_document.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(existing_document.id)
        assert data["document_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_update_document(
        self,
        superuser_client: AsyncClient,
        existing_document: Document,
    ):
        """Test updating a document."""
        update_data = {
            "document_version": "2.0",
            "version": 1,
        }

        response = await superuser_client.patch(
            f"/api/v1/admin/documents/{existing_document.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_version"] == "2.0"

    @pytest.mark.asyncio
    async def test_update_document_locales(
        self,
        superuser_client: AsyncClient,
        existing_document: Document,
    ):
        """Test updating document locales."""
        update_data = {
            "locales": [
                {
                    "locale": "en",
                    "title": "Updated Title",
                    "excerpt": "Updated excerpt",
                }
            ],
            "version": 1,
        }

        response = await superuser_client.patch(
            f"/api/v1/admin/documents/{existing_document.id}",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        en_locale = next(
            (l for l in data["locales"] if l["locale"] == "en"),
            None
        )
        assert en_locale is not None
        assert en_locale["title"] == "Updated Title"
        assert en_locale["excerpt"] == "Updated excerpt"

    @pytest.mark.asyncio
    async def test_delete_document(
        self,
        superuser_client: AsyncClient,
        existing_document: Document,
    ):
        """Test deleting a document."""
        response = await superuser_client.delete(
            f"/api/v1/admin/documents/{existing_document.id}"
        )

        assert response.status_code == 204

        # Verify document is not found
        response = await superuser_client.get(
            f"/api/v1/admin/documents/{existing_document.id}"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_publish_document(
        self,
        superuser_client: AsyncClient,
        existing_document: Document,
    ):
        """Test publishing a document."""
        response = await superuser_client.post(
            f"/api/v1/admin/documents/{existing_document.id}/publish"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None

    @pytest.mark.asyncio
    async def test_unpublish_document(
        self,
        db_session: AsyncSession,
        superuser_client: AsyncClient,
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
            slug=f"published-doc-{uuid4().hex[:8]}",
        )
        db_session.add(locale)
        await db_session.flush()

        response = await superuser_client.post(
            f"/api/v1/admin/documents/{document.id}/unpublish"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "draft"

    @pytest.mark.asyncio
    async def test_version_conflict(
        self,
        superuser_client: AsyncClient,
        existing_document: Document,
    ):
        """Test version conflict error."""
        update_data = {
            "document_version": "3.0",
            "version": 999,  # Wrong version
        }

        response = await superuser_client.patch(
            f"/api/v1/admin/documents/{existing_document.id}",
            json=update_data,
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_with_filters(
        self,
        db_session: AsyncSession,
        superuser_client: AsyncClient,
        test_tenant,
    ):
        """Test listing with status filter."""
        # Create draft and published documents
        for i, status in enumerate(["draft", "published"]):
            doc = Document(
                tenant_id=test_tenant.id,
                status=status,
                published_at=datetime.utcnow() if status == "published" else None,
            )
            db_session.add(doc)
            await db_session.flush()

            locale = DocumentLocale(
                document_id=doc.id,
                locale="en",
                title=f"Filter Test {i}",
                slug=f"filter-test-{i}-{uuid4().hex[:8]}",
            )
            db_session.add(locale)

        await db_session.flush()

        # Filter by draft status
        response = await superuser_client.get(
            "/api/v1/admin/documents",
            params={"status": "draft"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "draft" for item in data["items"])


class TestDocumentsAPIAuthentication:
    """Tests for authentication requirements."""

    @pytest.mark.asyncio
    async def test_admin_endpoints_require_auth(
        self,
        client: AsyncClient,
    ):
        """Test that admin endpoints require authentication."""
        endpoints = [
            ("GET", "/api/v1/admin/documents"),
            ("POST", "/api/v1/admin/documents"),
            ("GET", f"/api/v1/admin/documents/{uuid4()}"),
            ("PATCH", f"/api/v1/admin/documents/{uuid4()}"),
            ("DELETE", f"/api/v1/admin/documents/{uuid4()}"),
        ]

        for method, path in endpoints:
            if method == "GET":
                response = await client.get(path)
            elif method == "POST":
                response = await client.post(path, json={})
            elif method == "PATCH":
                response = await client.patch(path, json={})
            elif method == "DELETE":
                response = await client.delete(path)

            assert response.status_code == 401, f"Expected 401 for {method} {path}"

    @pytest.mark.asyncio
    async def test_public_endpoints_no_auth(
        self,
        client: AsyncClient,
        test_tenant,
    ):
        """Test that public endpoints don't require auth."""
        params = {
            "tenant_id": str(test_tenant.id),
            "locale": "en",
        }

        response = await client.get(
            "/api/v1/public/documents",
            params=params,
        )

        # Should not return 401
        assert response.status_code != 401

