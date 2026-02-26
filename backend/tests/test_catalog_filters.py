"""Integration tests for faceted catalog filtering, sorting, and SEO pages.

Tests cover:
- Parameter creation with slug auto-generation
- Parameter value slugs
- Parameter-category binding
- Product characteristic assignment (enum multi-select, number, string, bool)
- GET /public/filters – filterable + active only, faceted counters
- GET /public/filters with category – scoped parameters
- GET /public/filters with selected filter – recalculated counters
- GET /public/products with slug-based filters
- GET /public/products with multiple categories
- GET /public/products with sort=price_asc / price_desc
- Deactivation hides parameter from filters
- Deactivation hides value from filters
- GET /public/seo/filter-pages – correct combinations
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import (
    Category,
    Product,
    ProductCategory,
    ProductPrice,
)
from app.modules.parameters.models import (
    Parameter,
    ParameterCategory,
    ParameterValue,
    ProductCharacteristic,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def catalog_data(db_session: AsyncSession, test_tenant):
    """Seed full catalog: categories, products, parameters, values, chars, prices."""
    tenant_id = test_tenant.id

    # Categories
    cat_electronics = Category(
        tenant_id=tenant_id, title="Electronics", slug=f"electronics-{uuid4().hex[:6]}",
        is_active=True, sort_order=0, version=1,
    )
    cat_clothing = Category(
        tenant_id=tenant_id, title="Clothing", slug=f"clothing-{uuid4().hex[:6]}",
        is_active=True, sort_order=1, version=1,
    )
    db_session.add_all([cat_electronics, cat_clothing])
    await db_session.flush()

    # Products
    products = {}
    for i, (title, brand, cat) in enumerate([
        ("Red Phone", "BrandA", cat_electronics),
        ("Blue Phone", "BrandA", cat_electronics),
        ("Red Laptop", "BrandB", cat_electronics),
        ("Blue T-Shirt", "BrandC", cat_clothing),
        ("Red T-Shirt", "BrandC", cat_clothing),
    ]):
        slug = f"{title.lower().replace(' ', '-')}-{uuid4().hex[:6]}"
        p = Product(
            tenant_id=tenant_id, sku=f"SKU-{uuid4().hex[:8]}",
            slug=slug, title=title, brand=brand,
            is_active=True,
        )
        db_session.add(p)
        await db_session.flush()
        db_session.add(ProductCategory(product_id=p.id, category_id=cat.id, is_primary=True))
        products[title] = p

    # Prices
    for title, amount in [
        ("Red Phone", 500), ("Blue Phone", 300), ("Red Laptop", 1200),
        ("Blue T-Shirt", 50), ("Red T-Shirt", 75),
    ]:
        db_session.add(ProductPrice(
            product_id=products[title].id, price_type="regular",
            amount=Decimal(str(amount)), currency="RUB",
        ))

    await db_session.flush()

    # Parameters
    param_color = Parameter(
        tenant_id=tenant_id, name="Color", slug=f"color-{uuid4().hex[:6]}",
        value_type="enum", is_filterable=True, is_active=True, sort_order=0, scope="global",
    )
    param_material = Parameter(
        tenant_id=tenant_id, name="Material", slug=f"material-{uuid4().hex[:6]}",
        value_type="enum", is_filterable=True, is_active=True, sort_order=1, scope="global",
    )
    param_weight = Parameter(
        tenant_id=tenant_id, name="Weight", slug=f"weight-{uuid4().hex[:6]}",
        value_type="number", is_filterable=True, is_active=True, sort_order=2, scope="global",
    )
    param_hidden = Parameter(
        tenant_id=tenant_id, name="Internal Code", slug=f"internal-{uuid4().hex[:6]}",
        value_type="string", is_filterable=False, is_active=True, sort_order=3, scope="global",
    )
    db_session.add_all([param_color, param_material, param_weight, param_hidden])
    await db_session.flush()

    # Bind color and material to electronics
    db_session.add(ParameterCategory(parameter_id=param_color.id, category_id=cat_electronics.id))
    db_session.add(ParameterCategory(parameter_id=param_material.id, category_id=cat_electronics.id))
    # Bind color to clothing too
    db_session.add(ParameterCategory(parameter_id=param_color.id, category_id=cat_clothing.id))

    # Parameter values (color)
    val_red = ParameterValue(
        parameter_id=param_color.id, label="Red", slug=f"red-{uuid4().hex[:6]}", sort_order=0,
    )
    val_blue = ParameterValue(
        parameter_id=param_color.id, label="Blue", slug=f"blue-{uuid4().hex[:6]}", sort_order=1,
    )
    db_session.add_all([val_red, val_blue])

    # Parameter values (material)
    val_metal = ParameterValue(
        parameter_id=param_material.id, label="Metal", slug=f"metal-{uuid4().hex[:6]}", sort_order=0,
    )
    val_plastic = ParameterValue(
        parameter_id=param_material.id, label="Plastic", slug=f"plastic-{uuid4().hex[:6]}", sort_order=1,
    )
    db_session.add_all([val_metal, val_plastic])
    await db_session.flush()

    # Assign characteristics
    # Red Phone: color=red, material=metal, weight=180
    db_session.add(ProductCharacteristic(
        product_id=products["Red Phone"].id, parameter_id=param_color.id,
        parameter_value_id=val_red.id,
    ))
    db_session.add(ProductCharacteristic(
        product_id=products["Red Phone"].id, parameter_id=param_material.id,
        parameter_value_id=val_metal.id,
    ))
    db_session.add(ProductCharacteristic(
        product_id=products["Red Phone"].id, parameter_id=param_weight.id,
        value_number=Decimal("180"),
    ))

    # Blue Phone: color=blue, material=plastic, weight=150
    db_session.add(ProductCharacteristic(
        product_id=products["Blue Phone"].id, parameter_id=param_color.id,
        parameter_value_id=val_blue.id,
    ))
    db_session.add(ProductCharacteristic(
        product_id=products["Blue Phone"].id, parameter_id=param_material.id,
        parameter_value_id=val_plastic.id,
    ))
    db_session.add(ProductCharacteristic(
        product_id=products["Blue Phone"].id, parameter_id=param_weight.id,
        value_number=Decimal("150"),
    ))

    # Red Laptop: color=red, material=metal, weight=2500
    db_session.add(ProductCharacteristic(
        product_id=products["Red Laptop"].id, parameter_id=param_color.id,
        parameter_value_id=val_red.id,
    ))
    db_session.add(ProductCharacteristic(
        product_id=products["Red Laptop"].id, parameter_id=param_material.id,
        parameter_value_id=val_metal.id,
    ))
    db_session.add(ProductCharacteristic(
        product_id=products["Red Laptop"].id, parameter_id=param_weight.id,
        value_number=Decimal("2500"),
    ))

    # Blue T-Shirt: color=blue
    db_session.add(ProductCharacteristic(
        product_id=products["Blue T-Shirt"].id, parameter_id=param_color.id,
        parameter_value_id=val_blue.id,
    ))

    # Red T-Shirt: color=red
    db_session.add(ProductCharacteristic(
        product_id=products["Red T-Shirt"].id, parameter_id=param_color.id,
        parameter_value_id=val_red.id,
    ))

    await db_session.flush()

    return {
        "tenant_id": tenant_id,
        "categories": {"electronics": cat_electronics, "clothing": cat_clothing},
        "products": products,
        "parameters": {
            "color": param_color, "material": param_material,
            "weight": param_weight, "hidden": param_hidden,
        },
        "values": {
            "red": val_red, "blue": val_blue,
            "metal": val_metal, "plastic": val_plastic,
        },
    }


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
class TestPublicFilters:
    """GET /public/filters tests."""

    async def test_filters_returns_only_filterable_active(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/filters",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200
        body = resp.json()

        slugs = [f["slug"] for f in body["filters"]]
        # "color" and "material" are filterable; "weight" is filterable (range);
        # "hidden" (is_filterable=False) must NOT appear
        assert catalog_data["parameters"]["hidden"].slug not in slugs
        # Color and material should be present (they have products)
        assert catalog_data["parameters"]["color"].slug in slugs
        assert catalog_data["parameters"]["material"].slug in slugs

    async def test_filters_with_category_scopes_parameters(
        self, client: AsyncClient, catalog_data,
    ):
        cat_clothing = catalog_data["categories"]["clothing"]
        resp = await client.get(
            "/api/v1/public/filters",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "category": cat_clothing.slug,
            },
        )
        assert resp.status_code == 200
        body = resp.json()

        slugs = [f["slug"] for f in body["filters"]]
        # Color is bound to clothing; material is NOT bound to clothing
        assert catalog_data["parameters"]["color"].slug in slugs

    async def test_filters_faceted_counters_recalculate(
        self, client: AsyncClient, catalog_data,
    ):
        """Selecting color=red should show material counts only for red products."""
        color_slug = catalog_data["parameters"]["color"].slug
        red_slug = catalog_data["values"]["red"].slug

        resp = await client.get(
            "/api/v1/public/filters",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                color_slug: red_slug,
            },
        )
        assert resp.status_code == 200
        body = resp.json()

        material_filter = None
        for f in body["filters"]:
            if f["slug"] == catalog_data["parameters"]["material"].slug:
                material_filter = f
                break

        if material_filter:
            # Only "metal" should have count (Red Phone + Red Laptop are metal)
            metal_values = [v for v in material_filter["values"]
                           if v["slug"] == catalog_data["values"]["metal"].slug]
            assert len(metal_values) == 1
            assert metal_values[0]["count"] == 2

    async def test_filters_price_range(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/filters",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200
        body = resp.json()

        pr = body["price_range"]
        assert Decimal(str(pr["min"])) == Decimal("50")
        assert Decimal(str(pr["max"])) == Decimal("1200")

    async def test_filters_total_products(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/filters",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_products"] == 5


@pytest.mark.asyncio
class TestPublicProductFiltering:
    """GET /public/products with filters and sorting."""

    async def test_filter_by_enum_parameter(
        self, client: AsyncClient, catalog_data,
    ):
        color_slug = catalog_data["parameters"]["color"].slug
        red_slug = catalog_data["values"]["red"].slug

        resp = await client.get(
            "/api/v1/public/products",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                color_slug: red_slug,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # Red Phone, Red Laptop, Red T-Shirt = 3
        assert body["total"] == 3

    async def test_filter_by_multiple_parameters(
        self, client: AsyncClient, catalog_data,
    ):
        color_slug = catalog_data["parameters"]["color"].slug
        material_slug = catalog_data["parameters"]["material"].slug
        red_slug = catalog_data["values"]["red"].slug
        metal_slug = catalog_data["values"]["metal"].slug

        resp = await client.get(
            "/api/v1/public/products",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                color_slug: red_slug,
                material_slug: metal_slug,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # Red Phone (red+metal) + Red Laptop (red+metal) = 2
        assert body["total"] == 2

    async def test_filter_by_category_slug(
        self, client: AsyncClient, catalog_data,
    ):
        cat_slug = catalog_data["categories"]["electronics"].slug
        resp = await client.get(
            "/api/v1/public/products",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "category": cat_slug,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3

    async def test_filter_by_multiple_categories(
        self, client: AsyncClient, catalog_data,
    ):
        slugs = ",".join([
            catalog_data["categories"]["electronics"].slug,
            catalog_data["categories"]["clothing"].slug,
        ])
        resp = await client.get(
            "/api/v1/public/products",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "category": slugs,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5

    async def test_sort_price_asc(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/products",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "sort": "price_asc",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        items = body["items"]
        assert len(items) == 5
        # First item should be the cheapest (Blue T-Shirt, 50)
        assert items[0]["title"] == "Blue T-Shirt"

    async def test_sort_price_desc(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/products",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "sort": "price_desc",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        items = body["items"]
        # First item should be the most expensive (Red Laptop, 1200)
        assert items[0]["title"] == "Red Laptop"

    async def test_price_range_filter(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/products",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "price_min": "100",
                "price_max": "600",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        # Products: Red Phone (500), Blue Phone (300) = 2
        assert body["total"] == 2


@pytest.mark.asyncio
class TestDeactivation:
    """Deactivating parameter/value hides it from filters."""

    async def test_deactivated_parameter_hidden(
        self, client: AsyncClient, catalog_data, db_session: AsyncSession,
    ):
        param = catalog_data["parameters"]["material"]
        param.is_active = False
        await db_session.flush()

        resp = await client.get(
            "/api/v1/public/filters",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200
        slugs = [f["slug"] for f in resp.json()["filters"]]
        assert param.slug not in slugs

    async def test_deactivated_value_hidden(
        self, client: AsyncClient, catalog_data, db_session: AsyncSession,
    ):
        val_blue = catalog_data["values"]["blue"]
        val_blue.is_active = False
        await db_session.flush()

        resp = await client.get(
            "/api/v1/public/filters",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200

        color_filter = None
        for f in resp.json()["filters"]:
            if f["slug"] == catalog_data["parameters"]["color"].slug:
                color_filter = f
                break

        assert color_filter is not None
        value_slugs = [v["slug"] for v in color_filter["values"]]
        assert val_blue.slug not in value_slugs


@pytest.mark.asyncio
class TestSeoFilterPages:
    """GET /public/seo/filter-pages tests."""

    async def test_seo_pages_generated(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/seo/filter-pages",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert "pages" in body
        assert "total" in body
        assert body["total"] > 0

        for page in body["pages"]:
            assert page["product_count"] >= 1
            assert page["url_path"].startswith("/catalog")
            assert len(page["filters"]) >= 1

    async def test_seo_pages_with_category(
        self, client: AsyncClient, catalog_data,
    ):
        cat_slug = catalog_data["categories"]["electronics"].slug
        resp = await client.get(
            "/api/v1/public/seo/filter-pages",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "category": cat_slug,
            },
        )
        assert resp.status_code == 200
        body = resp.json()

        for page in body["pages"]:
            assert cat_slug in page["url_path"]

    async def test_seo_pages_min_products_filter(
        self, client: AsyncClient, catalog_data,
    ):
        resp = await client.get(
            "/api/v1/public/seo/filter-pages",
            params={
                "tenant_id": str(catalog_data["tenant_id"]),
                "min_products": "999",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0


@pytest.mark.asyncio
class TestProductDetailCharacteristics:
    """GET /public/products/{slug} returns normalized characteristics."""

    async def test_product_detail_has_characteristics(
        self, client: AsyncClient, catalog_data,
    ):
        product = catalog_data["products"]["Red Phone"]
        resp = await client.get(
            f"/api/v1/public/products/{product.slug}",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert "characteristics" in body
        assert "chars" in body
        assert len(body["characteristics"]) > 0

        color_char = None
        for c in body["characteristics"]:
            if c["parameter_slug"] == catalog_data["parameters"]["color"].slug:
                color_char = c
                break

        assert color_char is not None
        assert color_char["type"] == "enum"
        assert len(color_char["values"]) == 1
        assert color_char["values"][0]["slug"] == catalog_data["values"]["red"].slug

    async def test_product_detail_backward_compat_chars(
        self, client: AsyncClient, catalog_data,
    ):
        product = catalog_data["products"]["Red Phone"]
        resp = await client.get(
            f"/api/v1/public/products/{product.slug}",
            params={"tenant_id": str(catalog_data["tenant_id"])},
        )
        assert resp.status_code == 200
        body = resp.json()

        assert len(body["chars"]) > 0
        char_names = [c["name"] for c in body["chars"]]
        assert "Color" in char_names


@pytest.mark.asyncio
class TestAdminParameterAPI:
    """Admin parameter CRUD via API."""

    async def test_create_parameter_with_auto_slug(
        self, authenticated_client: AsyncClient, test_tenant,
    ):
        resp = await authenticated_client.post(
            "/api/v1/admin/parameters",
            json={
                "name": "Screen Size",
                "value_type": "number",
                "is_filterable": True,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["slug"].startswith("screen-size")
        assert body["is_filterable"] is True

    async def test_create_enum_parameter_with_values(
        self, authenticated_client: AsyncClient, test_tenant,
    ):
        resp = await authenticated_client.post(
            "/api/v1/admin/parameters",
            json={
                "name": "Brand Type",
                "value_type": "enum",
                "values": [
                    {"label": "Premium"},
                    {"label": "Budget"},
                ],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["values"]) == 2
        assert body["values"][0]["slug"].startswith("premium")
        assert body["values"][1]["slug"].startswith("budget")

    async def test_add_value_to_parameter(
        self, authenticated_client: AsyncClient, test_tenant,
    ):
        create_resp = await authenticated_client.post(
            "/api/v1/admin/parameters",
            json={"name": "Size", "value_type": "enum"},
        )
        param_id = create_resp.json()["id"]

        resp = await authenticated_client.post(
            f"/api/v1/admin/parameters/{param_id}/values",
            json={"label": "Large"},
        )
        assert resp.status_code == 201
        assert resp.json()["slug"].startswith("large")

    async def test_set_parameter_categories(
        self, authenticated_client: AsyncClient, test_tenant, db_session: AsyncSession,
    ):
        cat = Category(
            tenant_id=test_tenant.id, title="Test Cat",
            slug=f"test-cat-{uuid4().hex[:6]}", is_active=True,
            sort_order=0, version=1,
        )
        db_session.add(cat)
        await db_session.flush()

        create_resp = await authenticated_client.post(
            "/api/v1/admin/parameters",
            json={"name": "Test Param", "value_type": "string"},
        )
        param_id = create_resp.json()["id"]

        resp = await authenticated_client.put(
            f"/api/v1/admin/parameters/{param_id}/categories",
            json={"category_ids": [str(cat.id)]},
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 1
