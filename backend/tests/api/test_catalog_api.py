"""API tests for catalog module (products, categories)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category, Product
from tests.helpers import assert_error_response


@pytest.mark.api
@pytest.mark.asyncio
class TestCatalogPublicAPI:
    """Public catalog endpoints."""

    async def test_list_products_public_200(
        self, client: AsyncClient, test_tenant, db_session: AsyncSession,
    ) -> None:
        """GET /public/products should return 200 with tenant."""
        product = Product(
            tenant_id=test_tenant.id,
            sku=f"SKU-{uuid4().hex[:8]}",
            slug=f"product-{uuid4().hex[:8]}",
            title="Public Product",
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/public/products",
            params={"tenant_id": str(test_tenant.id)},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

    async def test_get_product_by_slug_public_200(
        self, client: AsyncClient, test_tenant, db_session: AsyncSession,
    ) -> None:
        """GET /public/products/{slug} should return 200 when product found."""
        slug = f"detail-product-{uuid4().hex[:8]}"
        product = Product(
            tenant_id=test_tenant.id,
            sku=f"SKU-{uuid4().hex[:8]}",
            slug=slug,
            title="Detail Product",
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/public/products/{slug}",
            params={"tenant_id": str(test_tenant.id)},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["slug"] == slug

    async def test_get_product_by_slug_public_404(
        self, client: AsyncClient, test_tenant,
    ) -> None:
        """GET /public/products/{slug} should return 404 when not found."""
        resp = await client.get(
            "/api/v1/public/products/nonexistent-slug",
            params={"tenant_id": str(test_tenant.id)},
        )

        assert_error_response(resp, 404, "not_found")

    async def test_list_categories_public_200(
        self, client: AsyncClient, test_tenant, db_session: AsyncSession,
    ) -> None:
        """GET /public/categories should return 200."""
        category = Category(
            tenant_id=test_tenant.id,
            title="Public Category",
            slug=f"cat-{uuid4().hex[:8]}",
            is_active=True,
            sort_order=0,
            version=1,
        )
        db_session.add(category)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/public/categories",
            params={"tenant_id": str(test_tenant.id)},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body


@pytest.mark.api
@pytest.mark.asyncio
class TestCatalogAdminAPI:
    """Admin catalog endpoints (auth required)."""

    async def test_admin_products_requires_auth(
        self, client: AsyncClient, test_tenant,
    ) -> None:
        """GET /admin/products should return 401 without auth."""
        resp = await client.get("/api/v1/admin/products")

        assert resp.status_code == 401

    async def test_admin_products_authenticated(
        self, authenticated_client: AsyncClient, test_tenant,
    ) -> None:
        """GET /admin/products should return 200 with valid auth."""
        resp = await authenticated_client.get("/api/v1/admin/products")

        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    async def test_create_product_requires_permission(
        self, content_manager_client: AsyncClient, test_tenant,
    ) -> None:
        """POST /admin/products should return 403 without catalog:create permission."""
        resp = await content_manager_client.post(
            "/api/v1/admin/products",
            json={
                "sku": "NEW-SKU",
                "slug": "new-product",
                "title": "New Product",
            },
        )

        assert resp.status_code == 403

    async def test_create_product_success(
        self, authenticated_client: AsyncClient, test_tenant,
    ) -> None:
        """POST /admin/products should create product with wildcard permissions."""
        unique = uuid4().hex[:8]
        resp = await authenticated_client.post(
            "/api/v1/admin/products",
            json={
                "sku": f"SKU-{unique}",
                "slug": f"product-{unique}",
                "title": "Created via API",
            },
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["sku"] == f"SKU-{unique}"
        assert body["slug"] == f"product-{unique}"
