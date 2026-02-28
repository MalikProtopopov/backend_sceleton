"""Integration tests for the product variants system.

Tests cover:
- Option group CRUD (create, list, update, delete)
- Option value CRUD (create, update, delete)
- Variant CRUD (create, get, list, update, soft-delete)
- Variant creates sets product.has_variants=True
- Variant matrix generation from option groups (is_active=False, base_price)
- Variant prices CRUD + price_from/price_to propagation
- Variant inclusions CRUD (create, list, update, delete)
- Variant images (list)
- Public product detail with variant data
- Public product list includes price_from/price_to
- Feature flag gating (403 when variants_module disabled)
- Simple products remain unchanged (has_variants=false)
- Variant delete recalculates price range
- is_default only-one-default constraint
"""

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import (
    Category,
    Product,
    ProductCategory,
    ProductPrice,
)
from app.modules.tenants.models import FeatureFlag
from app.modules.variants.models import (
    ProductOptionGroup,
    ProductOptionValue,
    ProductVariant,
    VariantInclusion,
    VariantOptionLink,
    VariantPrice,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def variant_product(db_session: AsyncSession, test_tenant):
    """Create a product with has_variants=true and option groups."""
    tid = test_tenant.id

    cat = Category(
        tenant_id=tid, title="Courses", slug=f"courses-{uuid4().hex[:6]}",
        is_active=True, sort_order=0, version=1,
    )
    db_session.add(cat)
    await db_session.flush()

    product = Product(
        tenant_id=tid,
        sku=f"COURSE-{uuid4().hex[:8]}",
        slug=f"python-course-{uuid4().hex[:6]}",
        title="Python Course",
        product_type="course",
        has_variants=True,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()

    db_session.add(ProductCategory(product_id=product.id, category_id=cat.id, is_primary=True))

    plan_group = ProductOptionGroup(
        id=uuid4(), product_id=product.id, tenant_id=tid,
        title="Tariff Plan", slug="plan", display_type="cards", sort_order=0,
    )
    db_session.add(plan_group)
    await db_session.flush()

    val_basic = ProductOptionValue(
        id=uuid4(), option_group_id=plan_group.id,
        title="Basic", slug="basic", sort_order=0,
    )
    val_premium = ProductOptionValue(
        id=uuid4(), option_group_id=plan_group.id,
        title="Premium", slug="premium", sort_order=1,
    )
    val_vip = ProductOptionValue(
        id=uuid4(), option_group_id=plan_group.id,
        title="VIP", slug="vip", sort_order=2,
    )
    db_session.add_all([val_basic, val_premium, val_vip])
    await db_session.flush()

    variants = []
    for idx, (ov, price_amt) in enumerate([
        (val_basic, Decimal("5000")),
        (val_premium, Decimal("12000")),
        (val_vip, Decimal("25000")),
    ]):
        v = ProductVariant(
            id=uuid4(), product_id=product.id, tenant_id=tid,
            sku=f"{product.sku}-{ov.slug.upper()}",
            slug=ov.slug, title=ov.title,
            is_default=(idx == 0), is_active=True, sort_order=idx,
        )
        db_session.add(v)
        await db_session.flush()

        db_session.add(VariantOptionLink(id=uuid4(), variant_id=v.id, option_value_id=ov.id))
        db_session.add(VariantPrice(
            id=uuid4(), variant_id=v.id,
            price_type="regular", amount=price_amt,
        ))

        if ov.slug != "basic":
            db_session.add(VariantInclusion(
                id=uuid4(), variant_id=v.id,
                title="Certificate", is_included=True, sort_order=0,
            ))

        variants.append(v)

    product.price_from = Decimal("5000")
    product.price_to = Decimal("25000")

    await db_session.flush()
    await db_session.commit()

    return {
        "product": product,
        "category": cat,
        "plan_group": plan_group,
        "values": [val_basic, val_premium, val_vip],
        "variants": variants,
    }


@pytest_asyncio.fixture
async def simple_product(db_session: AsyncSession, test_tenant):
    """Create a simple product without variants."""
    tid = test_tenant.id

    product = Product(
        tenant_id=tid,
        sku=f"BOOK-{uuid4().hex[:8]}",
        slug=f"book-{uuid4().hex[:6]}",
        title="Python Book",
        product_type="physical",
        has_variants=False,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()

    price = ProductPrice(
        product_id=product.id,
        price_type="regular",
        amount=Decimal("500"),
    )
    db_session.add(price)
    product.price_from = Decimal("500")
    product.price_to = Decimal("500")

    await db_session.flush()
    await db_session.commit()
    return product


# ============================================================================
# Tests: Option groups CRUD
# ============================================================================


@pytest.mark.asyncio
async def test_list_option_groups(
    authenticated_client: AsyncClient, variant_product,
):
    pid = variant_product["product"].id
    resp = await authenticated_client.get(f"/api/v1/admin/products/{pid}/option-groups")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["slug"] == "plan"
    assert len(data[0]["values"]) == 3


@pytest.mark.asyncio
async def test_create_option_group(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    resp = await authenticated_client.post(
        f"/api/v1/admin/products/{pid}/option-groups",
        json={
            "title": "Duration",
            "slug": "duration",
            "display_type": "buttons",
            "values": [
                {"title": "1 Month", "slug": "1m", "sort_order": 0},
                {"title": "1 Year", "slug": "1y", "sort_order": 1},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "duration"
    assert data["display_type"] == "buttons"
    assert len(data["values"]) == 2


@pytest.mark.asyncio
async def test_update_option_group(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    gid = variant_product["plan_group"].id
    resp = await authenticated_client.patch(
        f"/api/v1/admin/products/{pid}/option-groups/{gid}",
        json={"title": "Tariff Plan Updated", "display_type": "dropdown"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Tariff Plan Updated"
    assert data["display_type"] == "dropdown"


@pytest.mark.asyncio
async def test_delete_option_group(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    gid = variant_product["plan_group"].id
    resp = await authenticated_client.delete(
        f"/api/v1/admin/products/{pid}/option-groups/{gid}",
    )
    assert resp.status_code == 204

    resp2 = await authenticated_client.get(f"/api/v1/admin/products/{pid}/option-groups")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 0


# ============================================================================
# Tests: Option values CRUD
# ============================================================================


@pytest.mark.asyncio
async def test_create_option_value(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    gid = variant_product["plan_group"].id
    resp = await authenticated_client.post(
        f"/api/v1/admin/products/{pid}/option-groups/{gid}/values",
        json={"title": "Enterprise", "slug": "enterprise", "sort_order": 3},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Enterprise"
    assert data["slug"] == "enterprise"


@pytest.mark.asyncio
async def test_update_option_value(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    gid = variant_product["plan_group"].id
    vid = variant_product["values"][0].id
    resp = await authenticated_client.patch(
        f"/api/v1/admin/products/{pid}/option-groups/{gid}/values/{vid}",
        json={"title": "Basic Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Basic Updated"


@pytest.mark.asyncio
async def test_delete_option_value(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    gid = variant_product["plan_group"].id
    vid = variant_product["values"][2].id  # VIP
    resp = await authenticated_client.delete(
        f"/api/v1/admin/products/{pid}/option-groups/{gid}/values/{vid}",
    )
    assert resp.status_code == 204


# ============================================================================
# Tests: Variants CRUD
# ============================================================================


@pytest.mark.asyncio
async def test_list_variants(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    resp = await authenticated_client.get(f"/api/v1/admin/products/{pid}/variants")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["is_default"] is True
    assert len(data[0]["prices"]) == 1


@pytest.mark.asyncio
async def test_get_variant_detail(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    vid = variant_product["variants"][0].id
    resp = await authenticated_client.get(f"/api/v1/admin/products/{pid}/variants/{vid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(vid)
    assert data["is_default"] is True
    assert "prices" in data
    assert "option_values" in data
    assert "inclusions" in data
    assert "images" in data


@pytest.mark.asyncio
async def test_create_variant(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    val_ids = [str(v.id) for v in variant_product["values"][:1]]
    resp = await authenticated_client.post(
        f"/api/v1/admin/products/{pid}/variants",
        json={
            "sku": f"NEW-VAR-{uuid4().hex[:6]}",
            "slug": "new-variant",
            "title": "New Variant",
            "option_value_ids": val_ids,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "New Variant"


@pytest.mark.asyncio
async def test_create_variant_sets_has_variants(
    authenticated_client: AsyncClient, simple_product, db_session: AsyncSession,
):
    """Creating a variant on a simple product should set has_variants=True."""
    pid = simple_product.id
    resp = await authenticated_client.post(
        f"/api/v1/admin/products/{pid}/variants",
        json={
            "sku": f"VAR-{uuid4().hex[:6]}",
            "slug": f"variant-{uuid4().hex[:6]}",
            "title": "First Variant",
            "option_value_ids": [],
        },
    )
    assert resp.status_code == 201

    await db_session.refresh(simple_product)
    assert simple_product.has_variants is True


@pytest.mark.asyncio
async def test_update_variant(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    vid = variant_product["variants"][1].id
    resp = await authenticated_client.patch(
        f"/api/v1/admin/products/{pid}/variants/{vid}",
        json={"title": "Premium Updated", "description": "Updated desc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Premium Updated"
    assert data["description"] == "Updated desc"


@pytest.mark.asyncio
async def test_delete_variant_recalculates_price(
    authenticated_client: AsyncClient, variant_product, db_session: AsyncSession,
):
    """Soft-deleting the most expensive variant should reduce price_to."""
    pid = variant_product["product"].id
    vid = variant_product["variants"][2].id  # VIP (25000)

    resp = await authenticated_client.delete(
        f"/api/v1/admin/products/{pid}/variants/{vid}",
    )
    assert resp.status_code == 204

    await db_session.refresh(variant_product["product"])
    assert variant_product["product"].price_to <= Decimal("12000")


@pytest.mark.asyncio
async def test_is_default_constraint(authenticated_client: AsyncClient, variant_product):
    """Setting is_default on another variant should unset the previous default."""
    pid = variant_product["product"].id
    vid_premium = variant_product["variants"][1].id

    resp = await authenticated_client.patch(
        f"/api/v1/admin/products/{pid}/variants/{vid_premium}",
        json={"is_default": True},
    )
    assert resp.status_code == 200

    resp_list = await authenticated_client.get(f"/api/v1/admin/products/{pid}/variants")
    defaults = [v for v in resp_list.json() if v["is_default"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == str(vid_premium)


# ============================================================================
# Tests: Matrix generation
# ============================================================================


@pytest.mark.asyncio
async def test_generate_matrix(
    authenticated_client: AsyncClient, variant_product, db_session: AsyncSession, test_tenant,
):
    pid = variant_product["product"].id
    tid = test_tenant.id

    duration_group = ProductOptionGroup(
        id=uuid4(), product_id=pid, tenant_id=tid,
        title="Duration", slug="dur", display_type="buttons", sort_order=1,
    )
    db_session.add(duration_group)
    await db_session.flush()

    for slug, title, order in [("1m", "1 Month", 0), ("1y", "1 Year", 1)]:
        db_session.add(ProductOptionValue(
            id=uuid4(), option_group_id=duration_group.id,
            title=title, slug=slug, sort_order=order,
        ))
    await db_session.flush()
    await db_session.commit()

    resp = await authenticated_client.post(
        f"/api/v1/admin/products/{pid}/variants/generate",
        json={
            "option_group_ids": [
                str(variant_product["plan_group"].id),
                str(duration_group.id),
            ],
            "base_price": "1000",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["created_count"] >= 3
    for v in data["variants"]:
        assert v["is_active"] is False


# ============================================================================
# Tests: Variant Prices
# ============================================================================


@pytest.mark.asyncio
async def test_variant_price_crud(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    vid = variant_product["variants"][0].id

    resp = await authenticated_client.get(
        f"/api/v1/admin/products/{pid}/variants/{vid}/prices",
    )
    assert resp.status_code == 200

    resp = await authenticated_client.post(
        f"/api/v1/admin/products/{pid}/variants/{vid}/prices",
        json={"price_type": "sale", "amount": "3999"},
    )
    assert resp.status_code == 201
    price_id = resp.json()["id"]

    resp = await authenticated_client.patch(
        f"/api/v1/admin/products/{pid}/variants/{vid}/prices/{price_id}",
        json={"amount": "4999"},
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == "4999"

    resp = await authenticated_client.delete(
        f"/api/v1/admin/products/{pid}/variants/{vid}/prices/{price_id}",
    )
    assert resp.status_code == 204


# ============================================================================
# Tests: Variant Inclusions
# ============================================================================


@pytest.mark.asyncio
async def test_variant_inclusion_crud(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    vid = variant_product["variants"][1].id

    resp = await authenticated_client.post(
        f"/api/v1/admin/products/{pid}/variants/{vid}/inclusions",
        json={
            "title": "Personal mentor",
            "is_included": True,
            "group": "Support",
        },
    )
    assert resp.status_code == 201
    inc_id = resp.json()["id"]

    resp = await authenticated_client.get(
        f"/api/v1/admin/products/{pid}/variants/{vid}/inclusions",
    )
    assert resp.status_code == 200
    assert any(i["id"] == inc_id for i in resp.json())

    resp = await authenticated_client.patch(
        f"/api/v1/admin/products/{pid}/variants/{vid}/inclusions/{inc_id}",
        json={"title": "Personal mentor (updated)", "is_included": False},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Personal mentor (updated)"
    assert resp.json()["is_included"] is False

    resp = await authenticated_client.delete(
        f"/api/v1/admin/products/{pid}/variants/{vid}/inclusions/{inc_id}",
    )
    assert resp.status_code == 204


# ============================================================================
# Tests: Variant Images
# ============================================================================


@pytest.mark.asyncio
async def test_variant_images_list(authenticated_client: AsyncClient, variant_product):
    pid = variant_product["product"].id
    vid = variant_product["variants"][0].id

    resp = await authenticated_client.get(
        f"/api/v1/admin/products/{pid}/variants/{vid}/images",
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ============================================================================
# Tests: Public API with variants
# ============================================================================


@pytest.mark.asyncio
async def test_public_product_with_variants(
    client: AsyncClient, variant_product, test_tenant,
):
    slug = variant_product["product"].slug
    tid = test_tenant.id
    resp = await client.get(f"/api/v1/public/products/{slug}?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["product_type"] == "course"
    assert data["has_variants"] is True
    assert data["price_from"] is not None
    assert data["price_to"] is not None

    assert data["option_groups"] is not None
    assert len(data["option_groups"]) >= 1
    assert data["option_groups"][0]["slug"] == "plan"

    assert data["variants"] is not None
    assert len(data["variants"]) >= 1
    for v in data["variants"]:
        assert "prices" in v
        assert "in_stock" in v
        assert "options" in v


@pytest.mark.asyncio
async def test_public_simple_product_no_variants(
    client: AsyncClient, simple_product, test_tenant,
):
    slug = simple_product.slug
    tid = test_tenant.id
    resp = await client.get(f"/api/v1/public/products/{slug}?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["has_variants"] is False
    assert data["product_type"] == "physical"
    assert data.get("option_groups") is None
    assert data.get("variants") is None
    assert len(data["prices"]) >= 1


@pytest.mark.asyncio
async def test_public_product_list_includes_price_range(
    client: AsyncClient, variant_product, test_tenant,
):
    tid = test_tenant.id
    resp = await client.get(f"/api/v1/public/products?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()

    for item in data["items"]:
        assert "product_type" in item
        assert "has_variants" in item
        assert "price_from" in item
        assert "price_to" in item


@pytest.mark.asyncio
async def test_public_category_includes_variant_fields(
    client: AsyncClient, variant_product, test_tenant,
):
    """Category product list should include variant fields."""
    tid = test_tenant.id
    cat_slug = variant_product["category"].slug
    resp = await client.get(
        f"/api/v1/public/categories/{cat_slug}?tenant_id={tid}",
    )
    assert resp.status_code == 200
    data = resp.json()
    for item in data["products"]["items"]:
        assert "product_type" in item
        assert "has_variants" in item


# ============================================================================
# Tests: Feature flag gating
# ============================================================================


@pytest.mark.asyncio
async def test_variants_403_when_module_disabled(
    authenticated_client: AsyncClient, variant_product,
    db_session: AsyncSession, test_tenant,
):
    """Disabling variants_module should return 403 on variant endpoints."""
    await db_session.execute(
        update(FeatureFlag)
        .where(
            FeatureFlag.tenant_id == test_tenant.id,
            FeatureFlag.feature_name == "variants_module",
        )
        .values(enabled=False)
    )
    await db_session.flush()
    await db_session.commit()

    pid = variant_product["product"].id
    resp = await authenticated_client.get(
        f"/api/v1/admin/products/{pid}/option-groups",
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_public_product_no_variants_when_module_disabled(
    client: AsyncClient, variant_product,
    db_session: AsyncSession, test_tenant,
):
    """Public detail should not include variants when module is disabled."""
    await db_session.execute(
        update(FeatureFlag)
        .where(
            FeatureFlag.tenant_id == test_tenant.id,
            FeatureFlag.feature_name == "variants_module",
        )
        .values(enabled=False)
    )
    await db_session.flush()
    await db_session.commit()

    slug = variant_product["product"].slug
    tid = test_tenant.id
    resp = await client.get(f"/api/v1/public/products/{slug}?tenant_id={tid}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_variants"] is True
    assert data.get("option_groups") is None
    assert data.get("variants") is None
