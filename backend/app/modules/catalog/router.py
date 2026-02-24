"""API routes for catalog module."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import Pagination, PublicTenantId
from app.core.security import PermissionChecker, get_current_tenant_id
from app.middleware.feature_check import require_catalog, require_catalog_public
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryListResponse,
    CategoryPublicResponse,
    CategoryPublicTreeResponse,
    CategoryPublicWithProductsResponse,
    CategoryResponse,
    CategoryTreeResponse,
    CategoryUpdate,
    ProductAliasCreate,
    ProductAliasBulkResponse,
    ProductAliasResponse,
    ProductAnalogCreate,
    ProductAnalogResponse,
    ProductCharBulkResponse,
    ProductCharBulkUpdate,
    ProductCharResponse,
    ProductCreate,
    ProductDetailResponse,
    ProductImagePublicResponse,
    ProductImageReorderRequest,
    ProductImageResponse,
    ProductImageUpdateRequest,
    ProductListResponse,
    ProductPriceCreate,
    ProductPriceResponse,
    ProductPriceUpdate,
    ProductPublicDetailResponse,
    ProductPublicListResponse,
    ProductPublicResponse,
    ProductResponse,
    ProductUpdate,
    UOMCreate,
    UOMResponse,
    UOMUpdate,
)
from app.modules.catalog.service import (
    CategoryService,
    ProductImageService,
    ProductService,
    UOMService,
)

router = APIRouter()


# ============================================================================
# Public routes
# ============================================================================


@router.get(
    "/public/categories",
    response_model=CategoryPublicTreeResponse,
    summary="List published categories",
    tags=["Public - Catalog"],
    dependencies=[require_catalog_public],
)
async def list_categories_public(
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> CategoryPublicTreeResponse:
    service = CategoryService(db)
    items = await service.list_public(tenant_id)
    return CategoryPublicTreeResponse(
        items=[CategoryPublicResponse.model_validate(c) for c in items],
        total=len(items),
    )


@router.get(
    "/public/categories/{slug}",
    response_model=CategoryPublicWithProductsResponse,
    summary="Get category with products by slug",
    tags=["Public - Catalog"],
    dependencies=[require_catalog_public],
)
async def get_category_public(
    slug: str,
    pagination: Pagination,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> CategoryPublicWithProductsResponse:
    cat_service = CategoryService(db)
    category = await cat_service.get_by_slug_public(slug, tenant_id)

    prod_service = ProductService(db)
    products, total = await prod_service.list_published(
        tenant_id, page=pagination.page, page_size=pagination.page_size,
        category_id=category.id,
    )
    product_items = []
    for p in products:
        cover = next((img for img in (p.images or []) if img.is_cover), None)
        cover_url = cover.url if cover else (p.images[0].url if p.images else None)
        product_items.append(ProductPublicResponse(
            id=p.id, slug=p.slug, sku=p.sku, title=p.title,
            brand=p.brand, model=p.model, description=p.description,
            cover_url=cover_url,
        ))

    return CategoryPublicWithProductsResponse(
        category=CategoryPublicResponse.model_validate(category),
        products=ProductPublicListResponse(
            items=product_items, total=total,
            page=pagination.page, page_size=pagination.page_size,
        ),
    )


@router.get(
    "/public/products",
    response_model=ProductPublicListResponse,
    summary="List published products",
    tags=["Public - Catalog"],
    dependencies=[require_catalog_public],
)
async def list_products_public(
    pagination: Pagination,
    tenant_id: PublicTenantId,
    search: str | None = Query(default=None, max_length=200),
    brand: str | None = Query(default=None, max_length=255),
    category: UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ProductPublicListResponse:
    service = ProductService(db)
    products, total = await service.list_published(
        tenant_id, page=pagination.page, page_size=pagination.page_size,
        search=search, brand=brand, category_id=category,
    )
    items = []
    for p in products:
        cover = next((img for img in (p.images or []) if img.is_cover), None)
        cover_url = cover.url if cover else (p.images[0].url if p.images else None)
        items.append(ProductPublicResponse(
            id=p.id, slug=p.slug, sku=p.sku, title=p.title,
            brand=p.brand, model=p.model, description=p.description,
            cover_url=cover_url,
        ))
    return ProductPublicListResponse(
        items=items, total=total,
        page=pagination.page, page_size=pagination.page_size,
    )


@router.get(
    "/public/products/{slug}",
    response_model=ProductPublicDetailResponse,
    summary="Get product detail by slug",
    tags=["Public - Catalog"],
    dependencies=[require_catalog_public],
)
async def get_product_public(
    slug: str,
    tenant_id: PublicTenantId,
    db: AsyncSession = Depends(get_db),
) -> ProductPublicDetailResponse:
    service = ProductService(db)
    product = await service.get_by_slug_public(slug, tenant_id)

    categories = []
    for pc in (product.categories or []):
        if pc.category:
            categories.append(CategoryPublicResponse.model_validate(pc.category))

    return ProductPublicDetailResponse(
        id=product.id,
        slug=product.slug,
        sku=product.sku,
        title=product.title,
        brand=product.brand,
        model=product.model,
        description=product.description,
        images=[ProductImagePublicResponse.model_validate(img) for img in (product.images or [])],
        chars=[{"name": c.name, "value_text": c.value_text} for c in (product.chars or [])],
        categories=categories,
        prices=[{"price_type": p.price_type, "amount": p.amount, "currency": p.currency} for p in (product.prices or [])],
    )


# ============================================================================
# UOM routes
# ============================================================================


@router.get(
    "/admin/uoms",
    response_model=list[UOMResponse],
    summary="List units of measure",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_uoms(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[UOMResponse]:
    service = UOMService(db)
    items = await service.list_all(tenant_id)
    return [UOMResponse.model_validate(i) for i in items]


@router.post(
    "/admin/uoms",
    response_model=UOMResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create unit of measure",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def create_uom(
    data: UOMCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UOMResponse:
    service = UOMService(db)
    uom = await service.create(tenant_id, data.name, data.code, data.symbol)
    return UOMResponse.model_validate(uom)


@router.patch(
    "/admin/uoms/{uom_id}",
    response_model=UOMResponse,
    summary="Update unit of measure",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def update_uom(
    uom_id: UUID,
    data: UOMUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> UOMResponse:
    service = UOMService(db)
    uom = await service.update(uom_id, tenant_id, **data.model_dump(exclude_unset=True))
    return UOMResponse.model_validate(uom)


# ============================================================================
# Category routes
# ============================================================================


@router.get(
    "/admin/categories",
    response_model=CategoryListResponse,
    summary="List categories (paginated)",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_categories(
    pagination: Pagination,
    parent_id: UUID | None = Query(default=None),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CategoryListResponse:
    service = CategoryService(db)
    items, total = await service.list_categories(
        tenant_id, parent_id=parent_id,
        page=pagination.page, page_size=pagination.page_size,
    )
    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
    )


@router.get(
    "/admin/categories/tree",
    response_model=CategoryTreeResponse,
    summary="Get full category tree",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def get_category_tree(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CategoryTreeResponse:
    service = CategoryService(db)
    items = await service.list_tree(tenant_id)
    return CategoryTreeResponse(
        items=[CategoryResponse.model_validate(c) for c in items],
        total=len(items),
    )


@router.get(
    "/admin/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Get category by ID",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def get_category(
    category_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    service = CategoryService(db)
    category = await service.get_by_id(category_id, tenant_id)
    return CategoryResponse.model_validate(category)


@router.post(
    "/admin/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def create_category(
    data: CategoryCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    service = CategoryService(db)
    category = await service.create(tenant_id, data)
    return CategoryResponse.model_validate(category)


@router.patch(
    "/admin/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Update category",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> CategoryResponse:
    service = CategoryService(db)
    category = await service.update(category_id, tenant_id, data)
    return CategoryResponse.model_validate(category)


@router.delete(
    "/admin/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete category",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def delete_category(
    category_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = CategoryService(db)
    await service.soft_delete(category_id, tenant_id)


# ============================================================================
# Product routes
# ============================================================================


@router.get(
    "/admin/products",
    response_model=ProductListResponse,
    summary="List products",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_products(
    pagination: Pagination,
    search: str | None = Query(default=None, max_length=200),
    brand: str | None = Query(default=None, max_length=255),
    category_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None, alias="isActive"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    service = ProductService(db)
    items, total = await service.list_products(
        tenant_id, page=pagination.page, page_size=pagination.page_size,
        search=search, brand=brand, category_id=category_id, is_active=is_active,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total, page=pagination.page, page_size=pagination.page_size,
    )


@router.get(
    "/admin/products/{product_id}",
    response_model=ProductDetailResponse,
    summary="Get product detail",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def get_product(
    product_id: UUID,
    include: str | None = Query(
        default=None,
        description="Comma-separated: chars,aliases,categories,prices",
    ),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductDetailResponse:
    service = ProductService(db)
    includes = include.split(",") if include else None
    product = await service.get_with_includes(product_id, tenant_id, includes)
    return ProductDetailResponse.model_validate(product)


@router.post(
    "/admin/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def create_product(
    data: ProductCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    service = ProductService(db)
    product = await service.create(tenant_id, data)
    return ProductResponse.model_validate(product)


@router.patch(
    "/admin/products/{product_id}",
    response_model=ProductResponse,
    summary="Update product",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    service = ProductService(db)
    product = await service.update(product_id, tenant_id, data)
    return ProductResponse.model_validate(product)


@router.delete(
    "/admin/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete product",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def delete_product(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductService(db)
    await service.soft_delete(product_id, tenant_id)


# ============================================================================
# Product Characteristics (EAV) routes
# ============================================================================


@router.get(
    "/admin/products/{product_id}/chars",
    response_model=list[ProductCharResponse],
    summary="List product characteristics (EAV)",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_product_chars(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ProductCharResponse]:
    service = ProductService(db)
    items = await service.list_chars(product_id, tenant_id)
    return [ProductCharResponse.model_validate(c) for c in items]


@router.put(
    "/admin/products/{product_id}/chars",
    response_model=ProductCharBulkResponse,
    summary="Bulk create/update/delete product characteristics",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def bulk_update_product_chars(
    product_id: UUID,
    data: ProductCharBulkUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductCharBulkResponse:
    service = ProductService(db)
    result = await service.bulk_update_chars(product_id, tenant_id, data)
    return ProductCharBulkResponse(**result)


# ============================================================================
# Product Aliases routes
# ============================================================================


@router.get(
    "/admin/products/{product_id}/aliases",
    response_model=list[ProductAliasResponse],
    summary="List product aliases",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_product_aliases(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ProductAliasResponse]:
    service = ProductService(db)
    items = await service.list_aliases(product_id, tenant_id)
    return [ProductAliasResponse.model_validate(a) for a in items]


@router.post(
    "/admin/products/{product_id}/aliases",
    response_model=ProductAliasBulkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create product aliases",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def create_product_aliases(
    product_id: UUID,
    data: ProductAliasCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductAliasBulkResponse:
    service = ProductService(db)
    result = await service.bulk_create_aliases(product_id, tenant_id, data.aliases)
    return ProductAliasBulkResponse(**result)


@router.delete(
    "/admin/products/{product_id}/aliases/{alias_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product alias",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def delete_product_alias(
    product_id: UUID,
    alias_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductService(db)
    await service.delete_alias(product_id, alias_id, tenant_id)


# ============================================================================
# Product Analogs routes
# ============================================================================


@router.get(
    "/admin/products/{product_id}/analogs",
    response_model=list[ProductAnalogResponse],
    summary="List product analogs",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_product_analogs(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ProductAnalogResponse]:
    service = ProductService(db)
    return await service.list_analogs(product_id, tenant_id)


@router.post(
    "/admin/products/{product_id}/analogs",
    status_code=status.HTTP_201_CREATED,
    summary="Add product analog",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def add_product_analog(
    product_id: UUID,
    data: ProductAnalogCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    await service.add_analog(product_id, tenant_id, data)
    return {"success": True}


@router.delete(
    "/admin/products/{product_id}/analogs/{analog_product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove product analog",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def remove_product_analog(
    product_id: UUID,
    analog_product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductService(db)
    await service.remove_analog(product_id, analog_product_id, tenant_id)


# ============================================================================
# Product Prices routes
# ============================================================================


@router.get(
    "/admin/products/{product_id}/prices",
    response_model=list[ProductPriceResponse],
    summary="List product prices",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_product_prices(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ProductPriceResponse]:
    service = ProductService(db)
    items = await service.list_prices(product_id, tenant_id)
    return [ProductPriceResponse.model_validate(p) for p in items]


@router.post(
    "/admin/products/{product_id}/prices",
    response_model=ProductPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product price",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def create_product_price(
    product_id: UUID,
    data: ProductPriceCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductPriceResponse:
    service = ProductService(db)
    price = await service.create_price(product_id, tenant_id, data)
    return ProductPriceResponse.model_validate(price)


@router.patch(
    "/admin/products/{product_id}/prices/{price_id}",
    response_model=ProductPriceResponse,
    summary="Update product price",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def update_product_price(
    product_id: UUID,
    price_id: UUID,
    data: ProductPriceUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductPriceResponse:
    service = ProductService(db)
    price = await service.update_price(price_id, product_id, tenant_id, data)
    return ProductPriceResponse.model_validate(price)


@router.delete(
    "/admin/products/{product_id}/prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product price",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def delete_product_price(
    product_id: UUID,
    price_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductService(db)
    await service.delete_price(price_id, product_id, tenant_id)


# ============================================================================
# Product Categories routes
# ============================================================================


@router.put(
    "/admin/products/{product_id}/categories",
    summary="Set product categories (replace all)",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def set_product_categories(
    product_id: UUID,
    category_ids: list[UUID],
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ProductService(db)
    links = await service.set_categories(product_id, tenant_id, category_ids)
    return {"count": len(links)}


# ============================================================================
# Product Images routes
# ============================================================================


@router.get(
    "/admin/products/{product_id}/images",
    response_model=list[ProductImageResponse],
    summary="List product images",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:read"))],
)
async def list_product_images(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[ProductImageResponse]:
    service = ProductImageService(db)
    images = await service.list_images(product_id, tenant_id)
    return [ProductImageResponse.model_validate(i) for i in images]


@router.post(
    "/admin/products/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload product image",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:create"))],
)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
    alt: str | None = Form(default=None),
    is_cover: bool = Form(default=False),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    service = ProductImageService(db)
    image = await service.upload_image(product_id, tenant_id, file, alt=alt, is_cover=is_cover)
    return ProductImageResponse.model_validate(image)


@router.patch(
    "/admin/products/{product_id}/images/{image_id}",
    response_model=ProductImageResponse,
    summary="Update product image metadata",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def update_product_image(
    product_id: UUID,
    image_id: UUID,
    data: ProductImageUpdateRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> ProductImageResponse:
    service = ProductImageService(db)
    image = await service.update_image(
        product_id, image_id, tenant_id, alt=data.alt, sort_order=data.sort_order,
    )
    return ProductImageResponse.model_validate(image)


@router.delete(
    "/admin/products/{product_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete product image",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:delete"))],
)
async def delete_product_image(
    product_id: UUID,
    image_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductImageService(db)
    await service.delete_image(product_id, image_id, tenant_id)


@router.put(
    "/admin/products/{product_id}/images/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reorder product images",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def reorder_product_images(
    product_id: UUID,
    data: ProductImageReorderRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductImageService(db)
    await service.reorder_images(product_id, tenant_id, data.ordered_ids)


@router.post(
    "/admin/products/{product_id}/images/{image_id}/set-cover",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set image as product cover",
    dependencies=[require_catalog, Depends(PermissionChecker("catalog:update"))],
)
async def set_product_cover_image(
    product_id: UUID,
    image_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ProductImageService(db)
    await service.set_cover(product_id, image_id, tenant_id)
