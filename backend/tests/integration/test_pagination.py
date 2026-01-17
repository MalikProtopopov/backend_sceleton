"""Integration tests for pagination correctness."""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import (
    Article,
    ArticleLocale,
    ArticleStatus,
    Case,
    CaseLocale,
)
from app.modules.tenants.models import Tenant


@pytest_asyncio.fixture(scope="function")
async def cases_with_locale(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> list[Case]:
    """Create 25 published cases with 'ru' locale for pagination testing."""
    cases = []
    for i in range(25):
        case = Case(
            id=uuid4(),
            tenant_id=test_tenant.id,
            status=ArticleStatus.PUBLISHED.value,
            client_name=f"Client {i+1}",
            project_year=2024,
            is_featured=(i < 5),  # First 5 are featured
            sort_order=i,
        )
        db_session.add(case)
        await db_session.flush()

        # Add Russian locale
        locale = CaseLocale(
            id=uuid4(),
            case_id=case.id,
            locale="ru",
            slug=f"case-{i+1}-ru",
            title=f"Кейс {i+1}",
            excerpt=f"Описание кейса {i+1}",
        )
        db_session.add(locale)
        cases.append(case)

    await db_session.flush()
    return cases


@pytest_asyncio.fixture(scope="function")
async def cases_mixed_locale(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> list[Case]:
    """Create cases with mixed locales to test locale filtering."""
    cases = []
    for i in range(20):
        case = Case(
            id=uuid4(),
            tenant_id=test_tenant.id,
            status=ArticleStatus.PUBLISHED.value,
            client_name=f"Mixed Client {i+1}",
            project_year=2024,
            sort_order=i,
        )
        db_session.add(case)
        await db_session.flush()

        # Only even-indexed cases have 'ru' locale
        if i % 2 == 0:
            locale_ru = CaseLocale(
                id=uuid4(),
                case_id=case.id,
                locale="ru",
                slug=f"mixed-case-{i+1}-ru",
                title=f"Смешанный кейс {i+1}",
                excerpt=f"Описание {i+1}",
            )
            db_session.add(locale_ru)

        # All cases have 'en' locale
        locale_en = CaseLocale(
            id=uuid4(),
            case_id=case.id,
            locale="en",
            slug=f"mixed-case-{i+1}-en",
            title=f"Mixed Case {i+1}",
            excerpt=f"Description {i+1}",
        )
        db_session.add(locale_en)
        cases.append(case)

    await db_session.flush()
    return cases


@pytest_asyncio.fixture(scope="function")
async def articles_with_locale(
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> list[Article]:
    """Create 30 published articles with 'ru' locale for pagination testing."""
    articles = []
    for i in range(30):
        article = Article(
            id=uuid4(),
            tenant_id=test_tenant.id,
            status=ArticleStatus.PUBLISHED.value,
            view_count=0,
        )
        db_session.add(article)
        await db_session.flush()

        locale = ArticleLocale(
            id=uuid4(),
            article_id=article.id,
            locale="ru",
            slug=f"article-{i+1}-ru",
            title=f"Статья {i+1}",
            excerpt=f"Анонс статьи {i+1}",
            content=f"Содержание статьи {i+1}",
        )
        db_session.add(locale)
        articles.append(article)

    await db_session.flush()
    return articles


class TestPaginationCases:
    """Tests for cases pagination."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pagination_returns_correct_page_size(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        cases_with_locale: list[Case],
    ) -> None:
        """Test that page_size parameter is correctly applied."""
        response = await client.get(
            "/api/v1/public/cases",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 1,
                "page_size": 10,
                "locale": "ru",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 10
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pagination_offset_calculation(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        cases_with_locale: list[Case],
    ) -> None:
        """Test that offset is correctly calculated for different pages."""
        # Get first page
        response1 = await client.get(
            "/api/v1/public/cases",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 1,
                "page_size": 10,
                "locale": "ru",
            },
        )
        page1_ids = [item["id"] for item in response1.json()["items"]]

        # Get second page
        response2 = await client.get(
            "/api/v1/public/cases",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 2,
                "page_size": 10,
                "locale": "ru",
            },
        )
        page2_ids = [item["id"] for item in response2.json()["items"]]

        # Items should not overlap
        assert set(page1_ids).isdisjoint(set(page2_ids))

        # Both pages should have correct counts
        assert len(page1_ids) == 10
        assert len(page2_ids) == 10

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_pagination_last_page(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        cases_with_locale: list[Case],
    ) -> None:
        """Test that last page returns remaining items."""
        # 25 items with page_size=10 means page 3 has 5 items
        response = await client.get(
            "/api/v1/public/cases",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 3,
                "page_size": 10,
                "locale": "ru",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 5
        assert data["total"] == 25
        assert data["page"] == 3
        assert data["page_size"] == 10

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_locale_filtering_affects_total(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        cases_mixed_locale: list[Case],
    ) -> None:
        """Test that total count reflects locale filter."""
        # Request 'ru' locale - only 10 cases have it (even-indexed 0,2,4,6,8,10,12,14,16,18)
        response_ru = await client.get(
            "/api/v1/public/cases",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 1,
                "page_size": 20,
                "locale": "ru",
            },
        )

        assert response_ru.status_code == 200
        data_ru = response_ru.json()
        assert data_ru["total"] == 10
        assert len(data_ru["items"]) == 10

        # Request 'en' locale - all 20 cases have it
        response_en = await client.get(
            "/api/v1/public/cases",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 1,
                "page_size": 20,
                "locale": "en",
            },
        )

        assert response_en.status_code == 200
        data_en = response_en.json()
        assert data_en["total"] == 20
        assert len(data_en["items"]) == 20

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_default_page_size(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        cases_with_locale: list[Case],
    ) -> None:
        """Test that default page_size is 20."""
        response = await client.get(
            "/api/v1/public/cases",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 1,
                "locale": "ru",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Default page_size should be 20
        assert data["page_size"] == 20
        assert len(data["items"]) == 20


class TestPaginationArticles:
    """Tests for articles pagination."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_articles_pagination_correct_count(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        articles_with_locale: list[Article],
    ) -> None:
        """Test that articles pagination returns correct item count."""
        response = await client.get(
            "/api/v1/public/articles",
            params={
                "tenant_id": str(test_tenant.id),
                "page": 1,
                "page_size": 15,
                "locale": "ru",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 15
        assert data["total"] == 30
        assert data["page"] == 1
        assert data["page_size"] == 15

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_articles_no_duplicate_items(
        self,
        client: AsyncClient,
        test_tenant: Tenant,
        articles_with_locale: list[Article],
    ) -> None:
        """Test that paginated articles do not repeat across pages."""
        all_ids = set()

        for page in range(1, 4):  # 30 items / 15 per page = 2 full pages
            response = await client.get(
                "/api/v1/public/articles",
                params={
                    "tenant_id": str(test_tenant.id),
                    "page": page,
                    "page_size": 15,
                    "locale": "ru",
                },
            )

            data = response.json()
            page_ids = {item["id"] for item in data["items"]}

            # Check no duplicates with previous pages
            assert all_ids.isdisjoint(page_ids), f"Duplicate items found on page {page}"
            all_ids.update(page_ids)

