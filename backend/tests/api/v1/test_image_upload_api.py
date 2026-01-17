"""API tests for image upload endpoints.

Tests the image upload API endpoints with mocked S3.
Following TEST_RECOMENDATIONS.md structure.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import Article, ArticleLocale, Case, CaseLocale, Review
from app.modules.company.models import Service, ServiceLocale, Employee, EmployeeLocale


# Patch the image_upload_service at module level for all tests
@pytest.fixture(autouse=True)
def mock_image_upload_service():
    """Mock image upload service for all tests in this module."""
    with patch("app.modules.content.router.image_upload_service") as mock_content, \
         patch("app.modules.company.router.image_upload_service") as mock_company, \
         patch("app.modules.auth.router.image_upload_service") as mock_auth, \
         patch("app.modules.tenants.router.image_upload_service") as mock_tenants:
        
        # Configure all mocks
        for mock in [mock_content, mock_company, mock_auth, mock_tenants]:
            mock.upload_image = AsyncMock(
                return_value="https://s3.example.com/bucket/uploaded-image.jpg"
            )
            mock.delete_image = AsyncMock(return_value=True)
        
        yield {
            "content": mock_content,
            "company": mock_company,
            "auth": mock_auth,
            "tenants": mock_tenants,
        }


class TestArticleCoverImageUpload:
    """Tests for article cover image upload endpoint."""

    @pytest_asyncio.fixture
    async def test_article(
        self, db_session: AsyncSession, test_tenant
    ) -> Article:
        """Create a test article."""
        article = Article(
            id=uuid4(),
            tenant_id=test_tenant.id,
            status="draft",
            reading_time_minutes=5,
        )
        db_session.add(article)
        await db_session.flush()

        locale = ArticleLocale(
            article_id=article.id,
            locale="en",
            title="Test Article",
            slug=f"test-article-{uuid4().hex[:8]}",
            content="Test content",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(article, ["locales"])
        return article

    @pytest.mark.asyncio
    async def test_upload_cover_image_success(
        self,
        superuser_client: AsyncClient,
        test_article: Article,
        mock_image_upload_service,
    ):
        """Test successful cover image upload."""
        # Create fake image file
        image_content = b"\x89PNG\r\n\x1a\n" + b"fake png content"  # PNG magic bytes

        response = await superuser_client.post(
            f"/api/v1/admin/articles/{test_article.id}/cover-image",
            files={"file": ("test.png", io.BytesIO(image_content), "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_article.id)
        mock_image_upload_service["content"].upload_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_cover_image_invalid_type(
        self,
        superuser_client: AsyncClient,
        test_article: Article,
        mock_image_upload_service,
    ):
        """Test upload fails for invalid file type."""
        pdf_content = b"%PDF-1.4 fake pdf content"
        
        # Make the service raise an error for invalid type
        from app.core.image_upload import ImageUploadError
        mock_image_upload_service["content"].upload_image.side_effect = ImageUploadError(
            "Invalid file type: application/pdf. Allowed types: image/gif, image/jpeg, image/png, image/webp"
        )

        response = await superuser_client.post(
            f"/api/v1/admin/articles/{test_article.id}/cover-image",
            files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_cover_image_not_found(
        self,
        superuser_client: AsyncClient,
        mock_image_upload_service,
    ):
        """Test upload fails for non-existent article."""
        fake_id = uuid4()
        image_content = b"\x89PNG\r\n\x1a\n" + b"fake png content"

        response = await superuser_client.post(
            f"/api/v1/admin/articles/{fake_id}/cover-image",
            files={"file": ("test.png", io.BytesIO(image_content), "image/png")},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_upload_cover_image_unauthorized(
        self,
        client: AsyncClient,
        test_article: Article,
        mock_image_upload_service,
    ):
        """Test upload fails without authentication."""
        image_content = b"\x89PNG\r\n\x1a\n" + b"fake png content"

        response = await client.post(
            f"/api/v1/admin/articles/{test_article.id}/cover-image",
            files={"file": ("test.png", io.BytesIO(image_content), "image/png")},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_cover_image_success(
        self,
        superuser_client: AsyncClient,
        test_article: Article,
        db_session: AsyncSession,
        mock_image_upload_service,
    ):
        """Test successful cover image deletion."""
        # Set a cover image URL first
        test_article.cover_image_url = "https://s3.example.com/bucket/old-image.jpg"
        await db_session.flush()

        response = await superuser_client.delete(
            f"/api/v1/admin/articles/{test_article.id}/cover-image",
        )

        assert response.status_code == 204
        mock_image_upload_service["content"].delete_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_cover_image_not_found(
        self,
        superuser_client: AsyncClient,
        mock_image_upload_service,
    ):
        """Test delete fails for non-existent article."""
        fake_id = uuid4()

        response = await superuser_client.delete(
            f"/api/v1/admin/articles/{fake_id}/cover-image",
        )

        assert response.status_code == 404


class TestCaseCoverImageUpload:
    """Tests for case cover image upload endpoint."""

    @pytest_asyncio.fixture
    async def test_case(
        self, db_session: AsyncSession, test_tenant
    ) -> Case:
        """Create a test case."""
        case = Case(
            id=uuid4(),
            tenant_id=test_tenant.id,
            status="draft",
            client_name="Test Client",
        )
        db_session.add(case)
        await db_session.flush()

        locale = CaseLocale(
            case_id=case.id,
            locale="en",
            title="Test Case",
            slug=f"test-case-{uuid4().hex[:8]}",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(case, ["locales"])
        return case

    @pytest.mark.asyncio
    async def test_upload_cover_image_success(
        self,
        superuser_client: AsyncClient,
        test_case: Case,
        mock_image_upload_service,
    ):
        """Test successful case cover image upload."""
        image_content = b"\xFF\xD8\xFF" + b"fake jpeg content"  # JPEG magic bytes

        response = await superuser_client.post(
            f"/api/v1/admin/cases/{test_case.id}/cover-image",
            files={"file": ("test.jpg", io.BytesIO(image_content), "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_case.id)


class TestServiceImageUpload:
    """Tests for service image upload endpoint."""

    @pytest_asyncio.fixture
    async def test_service(
        self, db_session: AsyncSession, test_tenant
    ) -> Service:
        """Create a test service."""
        service = Service(
            id=uuid4(),
            tenant_id=test_tenant.id,
            icon="briefcase",
            is_published=False,
        )
        db_session.add(service)
        await db_session.flush()

        locale = ServiceLocale(
            service_id=service.id,
            locale="en",
            title="Test Service",
            slug=f"test-service-{uuid4().hex[:8]}",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(service, ["locales"])
        return service

    @pytest.mark.asyncio
    async def test_upload_image_success(
        self,
        superuser_client: AsyncClient,
        test_service: Service,
        mock_image_upload_service,
    ):
        """Test successful service image upload."""
        image_content = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"fake webp content"

        response = await superuser_client.post(
            f"/api/v1/admin/services/{test_service.id}/image",
            files={"file": ("test.webp", io.BytesIO(image_content), "image/webp")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_service.id)


class TestEmployeePhotoUpload:
    """Tests for employee photo upload endpoint."""

    @pytest_asyncio.fixture
    async def test_employee(
        self, db_session: AsyncSession, test_tenant
    ) -> Employee:
        """Create a test employee."""
        employee = Employee(
            id=uuid4(),
            tenant_id=test_tenant.id,
            email="test@example.com",
            is_published=False,
        )
        db_session.add(employee)
        await db_session.flush()

        locale = EmployeeLocale(
            employee_id=employee.id,
            locale="en",
            first_name="John",
            last_name="Doe",
            slug=f"john-doe-{uuid4().hex[:8]}",
            position="Developer",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(employee, ["locales"])
        return employee

    @pytest.mark.asyncio
    async def test_upload_photo_success(
        self,
        superuser_client: AsyncClient,
        test_employee: Employee,
        mock_image_upload_service,
    ):
        """Test successful employee photo upload."""
        image_content = b"GIF89a" + b"fake gif content"  # GIF magic bytes

        response = await superuser_client.post(
            f"/api/v1/admin/employees/{test_employee.id}/photo",
            files={"file": ("test.gif", io.BytesIO(image_content), "image/gif")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_employee.id)


class TestReviewAuthorPhotoUpload:
    """Tests for review author photo upload endpoint."""

    @pytest_asyncio.fixture
    async def test_review(
        self, db_session: AsyncSession, test_tenant
    ) -> Review:
        """Create a test review."""
        review = Review(
            id=uuid4(),
            tenant_id=test_tenant.id,
            rating=5,
            author_name="Test Author",
            content="Great service!",
            status="pending",
        )
        db_session.add(review)
        await db_session.flush()
        return review

    @pytest.mark.asyncio
    async def test_upload_author_photo_success(
        self,
        superuser_client: AsyncClient,
        test_review: Review,
        mock_image_upload_service,
    ):
        """Test successful review author photo upload."""
        image_content = b"\x89PNG\r\n\x1a\n" + b"fake png content"

        response = await superuser_client.post(
            f"/api/v1/admin/reviews/{test_review.id}/author-photo",
            files={"file": ("test.png", io.BytesIO(image_content), "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_review.id)


class TestUserAvatarUpload:
    """Tests for user avatar upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_my_avatar_success(
        self,
        authenticated_client: AsyncClient,
        test_user,
        mock_image_upload_service,
    ):
        """Test successful own avatar upload."""
        image_content = b"\x89PNG\r\n\x1a\n" + b"fake png content"

        response = await authenticated_client.post(
            "/api/v1/auth/me/avatar",
            files={"file": ("avatar.png", io.BytesIO(image_content), "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_delete_my_avatar_success(
        self,
        authenticated_client: AsyncClient,
        test_user,
        db_session: AsyncSession,
        mock_image_upload_service,
    ):
        """Test successful own avatar deletion."""
        # Set avatar URL first
        test_user.avatar_url = "https://s3.example.com/bucket/old-avatar.jpg"
        await db_session.flush()

        response = await authenticated_client.delete("/api/v1/auth/me/avatar")

        assert response.status_code == 204


class TestImageUploadValidation:
    """Tests for image upload validation across all endpoints."""

    @pytest_asyncio.fixture
    async def test_article(
        self, db_session: AsyncSession, test_tenant
    ) -> Article:
        """Create a test article."""
        article = Article(
            id=uuid4(),
            tenant_id=test_tenant.id,
            status="draft",
        )
        db_session.add(article)
        await db_session.flush()

        locale = ArticleLocale(
            article_id=article.id,
            locale="en",
            title="Test Article",
            slug=f"test-article-{uuid4().hex[:8]}",
            content="Test content",
        )
        db_session.add(locale)
        await db_session.flush()
        await db_session.refresh(article, ["locales"])
        return article

    @pytest.mark.asyncio
    async def test_rejects_svg_file(
        self,
        superuser_client: AsyncClient,
        test_article: Article,
        mock_image_upload_service,
    ):
        """Test upload rejects SVG files (security risk)."""
        svg_content = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'

        # Configure mock to raise error for invalid type
        from app.core.image_upload import ImageUploadError
        mock_image_upload_service["content"].upload_image.side_effect = ImageUploadError(
            "Invalid file type: image/svg+xml"
        )

        response = await superuser_client.post(
            f"/api/v1/admin/articles/{test_article.id}/cover-image",
            files={"file": ("test.svg", io.BytesIO(svg_content), "image/svg+xml")},
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rejects_executable(
        self,
        superuser_client: AsyncClient,
        test_article: Article,
        mock_image_upload_service,
    ):
        """Test upload rejects executable files."""
        exe_content = b"MZ" + b"\x00" * 100  # PE executable magic bytes

        # Configure mock to raise error for invalid type
        from app.core.image_upload import ImageUploadError
        mock_image_upload_service["content"].upload_image.side_effect = ImageUploadError(
            "Invalid file type: application/x-msdownload"
        )

        response = await superuser_client.post(
            f"/api/v1/admin/articles/{test_article.id}/cover-image",
            files={"file": ("test.exe", io.BytesIO(exe_content), "application/x-msdownload")},
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_accepts_all_valid_formats(
        self,
        superuser_client: AsyncClient,
        test_article: Article,
        mock_image_upload_service,
    ):
        """Test upload accepts all valid image formats (JPEG, PNG, WebP, GIF)."""
        test_cases = [
            ("test.jpg", b"\xFF\xD8\xFF\xE0\x00\x10JFIF", "image/jpeg"),
            ("test.png", b"\x89PNG\r\n\x1a\n", "image/png"),
            ("test.webp", b"RIFF\x00\x00\x00\x00WEBP", "image/webp"),
            ("test.gif", b"GIF89a", "image/gif"),
        ]

        for filename, content, mime_type in test_cases:
            # Reset mock for each test
            mock_image_upload_service["content"].upload_image.reset_mock()
            mock_image_upload_service["content"].upload_image.side_effect = None
            mock_image_upload_service["content"].upload_image.return_value = \
                f"https://s3.example.com/bucket/{filename}"

            response = await superuser_client.post(
                f"/api/v1/admin/articles/{test_article.id}/cover-image",
                files={"file": (filename, io.BytesIO(content + b"fake content"), mime_type)},
            )

            assert response.status_code == 200, f"Failed for {mime_type}"
            mock_image_upload_service["content"].upload_image.assert_called_once()

