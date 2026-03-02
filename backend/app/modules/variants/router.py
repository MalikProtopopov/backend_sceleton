"""API routes for the variants module (admin-only)."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import PermissionChecker, get_current_tenant_id
from app.middleware.feature_check import require_catalog, require_limit, require_variants
from app.modules.variants.schemas import (
    OptionGroupCreate,
    OptionGroupResponse,
    OptionGroupUpdate,
    OptionValueCreate,
    OptionValueResponse,
    OptionValueUpdate,
    VariantCreate,
    VariantDetailResponse,
    VariantGenerateRequest,
    VariantGenerateResponse,
    VariantImageResponse,
    VariantInclusionCreate,
    VariantInclusionResponse,
    VariantInclusionUpdate,
    VariantPriceCreate,
    VariantPriceResponse,
    VariantPriceUpdate,
    VariantResponse,
    VariantUpdate,
)
from app.modules.variants.service import (
    OptionGroupService,
    VariantImageService,
    VariantInclusionService,
    VariantPriceService,
    VariantService,
)

router = APIRouter()

_read_deps = [require_catalog, require_variants, Depends(PermissionChecker("catalog:read"))]
_create_deps = [require_catalog, require_variants, require_limit("max_variants"), Depends(PermissionChecker("catalog:create"))]
_update_deps = [require_catalog, require_variants, Depends(PermissionChecker("catalog:update"))]
_delete_deps = [require_catalog, require_variants, Depends(PermissionChecker("catalog:delete"))]


def _variant_detail(v) -> VariantDetailResponse:
    """Build enriched variant response."""
    return VariantDetailResponse(
        id=v.id,
        product_id=v.product_id,
        tenant_id=v.tenant_id,
        sku=v.sku,
        slug=v.slug,
        title=v.title,
        description=v.description,
        is_default=v.is_default,
        is_active=v.is_active,
        sort_order=v.sort_order,
        stock_quantity=v.stock_quantity,
        weight=v.weight,
        created_at=v.created_at,
        updated_at=v.updated_at,
        prices=[VariantPriceResponse.model_validate(p) for p in (v.prices or [])],
        option_values=[OptionValueResponse.model_validate(ol.option_value) for ol in (v.option_links or []) if ol.option_value],
        inclusions=[VariantInclusionResponse.model_validate(i) for i in (v.inclusions or [])],
        images=[VariantImageResponse.model_validate(img) for img in (v.images or [])],
    )


# ============================================================================
# Option Groups
# ============================================================================


@router.get(
    "/admin/products/{product_id}/option-groups",
    response_model=list[OptionGroupResponse],
    summary="List option groups for a product",
    dependencies=_read_deps,
)
async def list_option_groups(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[OptionGroupResponse]:
    svc = OptionGroupService(db)
    groups = await svc.list_for_product(product_id, tenant_id)
    return [OptionGroupResponse.model_validate(g) for g in groups]


@router.post(
    "/admin/products/{product_id}/option-groups",
    response_model=OptionGroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an option group",
    dependencies=_create_deps,
)
async def create_option_group(
    product_id: UUID,
    data: OptionGroupCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OptionGroupResponse:
    svc = OptionGroupService(db)
    group = await svc.create(product_id, tenant_id, data)
    return OptionGroupResponse.model_validate(group)


@router.patch(
    "/admin/products/{product_id}/option-groups/{group_id}",
    response_model=OptionGroupResponse,
    summary="Update an option group",
    dependencies=_update_deps,
)
async def update_option_group(
    product_id: UUID,
    group_id: UUID,
    data: OptionGroupUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OptionGroupResponse:
    svc = OptionGroupService(db)
    group = await svc.update(group_id, product_id, tenant_id, data)
    return OptionGroupResponse.model_validate(group)


@router.delete(
    "/admin/products/{product_id}/option-groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an option group",
    dependencies=_delete_deps,
)
async def delete_option_group(
    product_id: UUID,
    group_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = OptionGroupService(db)
    await svc.delete(group_id, product_id, tenant_id)


# ============================================================================
# Option Values
# ============================================================================


@router.post(
    "/admin/products/{product_id}/option-groups/{group_id}/values",
    response_model=OptionValueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a value to an option group",
    dependencies=_create_deps,
)
async def create_option_value(
    product_id: UUID,
    group_id: UUID,
    data: OptionValueCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OptionValueResponse:
    svc = OptionGroupService(db)
    val = await svc.create_value(group_id, product_id, tenant_id, data)
    return OptionValueResponse.model_validate(val)


@router.patch(
    "/admin/products/{product_id}/option-groups/{group_id}/values/{value_id}",
    response_model=OptionValueResponse,
    summary="Update an option value",
    dependencies=_update_deps,
)
async def update_option_value(
    product_id: UUID,
    group_id: UUID,
    value_id: UUID,
    data: OptionValueUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> OptionValueResponse:
    svc = OptionGroupService(db)
    val = await svc.update_value(value_id, group_id, product_id, tenant_id, data)
    return OptionValueResponse.model_validate(val)


@router.delete(
    "/admin/products/{product_id}/option-groups/{group_id}/values/{value_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an option value",
    dependencies=_delete_deps,
)
async def delete_option_value(
    product_id: UUID,
    group_id: UUID,
    value_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = OptionGroupService(db)
    await svc.delete_value(value_id, group_id, product_id, tenant_id)


# ============================================================================
# Variants
# ============================================================================


@router.get(
    "/admin/products/{product_id}/variants",
    response_model=list[VariantDetailResponse],
    summary="List variants for a product",
    dependencies=_read_deps,
)
async def list_variants(
    product_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[VariantDetailResponse]:
    svc = VariantService(db)
    variants = await svc.list_for_product(product_id, tenant_id)
    return [_variant_detail(v) for v in variants]


@router.get(
    "/admin/products/{product_id}/variants/{variant_id}",
    response_model=VariantDetailResponse,
    summary="Get variant detail",
    dependencies=_read_deps,
)
async def get_variant(
    product_id: UUID,
    variant_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantDetailResponse:
    svc = VariantService(db)
    v = await svc.get_by_id(variant_id, product_id, tenant_id)
    return _variant_detail(v)


@router.post(
    "/admin/products/{product_id}/variants",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a variant",
    dependencies=_create_deps,
)
async def create_variant(
    product_id: UUID,
    data: VariantCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantResponse:
    svc = VariantService(db)
    variant = await svc.create(product_id, tenant_id, data)
    return VariantResponse.model_validate(variant)


@router.patch(
    "/admin/products/{product_id}/variants/{variant_id}",
    response_model=VariantResponse,
    summary="Update a variant",
    dependencies=_update_deps,
)
async def update_variant(
    product_id: UUID,
    variant_id: UUID,
    data: VariantUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantResponse:
    svc = VariantService(db)
    variant = await svc.update(variant_id, product_id, tenant_id, data)
    return VariantResponse.model_validate(variant)


@router.delete(
    "/admin/products/{product_id}/variants/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a variant",
    dependencies=_delete_deps,
)
async def delete_variant(
    product_id: UUID,
    variant_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = VariantService(db)
    await svc.soft_delete(variant_id, product_id, tenant_id)


@router.post(
    "/admin/products/{product_id}/variants/generate",
    response_model=VariantGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Auto-generate variant matrix from option groups",
    dependencies=_create_deps,
)
async def generate_variants(
    product_id: UUID,
    data: VariantGenerateRequest,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantGenerateResponse:
    svc = VariantService(db)
    created = await svc.generate_matrix(
        product_id, tenant_id, data.option_group_ids, data.base_price,
    )
    return VariantGenerateResponse(
        created_count=len(created),
        variants=[VariantResponse.model_validate(v) for v in created],
    )


# ============================================================================
# Variant Prices
# ============================================================================


@router.get(
    "/admin/products/{product_id}/variants/{variant_id}/prices",
    response_model=list[VariantPriceResponse],
    summary="List variant prices",
    dependencies=_read_deps,
)
async def list_variant_prices(
    product_id: UUID,
    variant_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[VariantPriceResponse]:
    svc = VariantPriceService(db)
    prices = await svc.list_prices(variant_id, product_id, tenant_id)
    return [VariantPriceResponse.model_validate(p) for p in prices]


@router.post(
    "/admin/products/{product_id}/variants/{variant_id}/prices",
    response_model=VariantPriceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create variant price",
    dependencies=_create_deps,
)
async def create_variant_price(
    product_id: UUID,
    variant_id: UUID,
    data: VariantPriceCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantPriceResponse:
    svc = VariantPriceService(db)
    price = await svc.create_price(variant_id, product_id, tenant_id, data)
    return VariantPriceResponse.model_validate(price)


@router.patch(
    "/admin/products/{product_id}/variants/{variant_id}/prices/{price_id}",
    response_model=VariantPriceResponse,
    summary="Update variant price",
    dependencies=_update_deps,
)
async def update_variant_price(
    product_id: UUID,
    variant_id: UUID,
    price_id: UUID,
    data: VariantPriceUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantPriceResponse:
    svc = VariantPriceService(db)
    price = await svc.update_price(price_id, variant_id, product_id, tenant_id, data)
    return VariantPriceResponse.model_validate(price)


@router.delete(
    "/admin/products/{product_id}/variants/{variant_id}/prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete variant price",
    dependencies=_delete_deps,
)
async def delete_variant_price(
    product_id: UUID,
    variant_id: UUID,
    price_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = VariantPriceService(db)
    await svc.delete_price(price_id, variant_id, product_id, tenant_id)


# ============================================================================
# Variant Inclusions
# ============================================================================


@router.get(
    "/admin/products/{product_id}/variants/{variant_id}/inclusions",
    response_model=list[VariantInclusionResponse],
    summary="List variant inclusions",
    dependencies=_read_deps,
)
async def list_variant_inclusions(
    product_id: UUID,
    variant_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[VariantInclusionResponse]:
    svc = VariantInclusionService(db)
    items = await svc.list_inclusions(variant_id, product_id, tenant_id)
    return [VariantInclusionResponse.model_validate(i) for i in items]


@router.post(
    "/admin/products/{product_id}/variants/{variant_id}/inclusions",
    response_model=VariantInclusionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create variant inclusion",
    dependencies=_create_deps,
)
async def create_variant_inclusion(
    product_id: UUID,
    variant_id: UUID,
    data: VariantInclusionCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantInclusionResponse:
    svc = VariantInclusionService(db)
    inc = await svc.create(variant_id, product_id, tenant_id, data)
    return VariantInclusionResponse.model_validate(inc)


@router.patch(
    "/admin/products/{product_id}/variants/{variant_id}/inclusions/{inclusion_id}",
    response_model=VariantInclusionResponse,
    summary="Update variant inclusion",
    dependencies=_update_deps,
)
async def update_variant_inclusion(
    product_id: UUID,
    variant_id: UUID,
    inclusion_id: UUID,
    data: VariantInclusionUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantInclusionResponse:
    svc = VariantInclusionService(db)
    inc = await svc.update(inclusion_id, variant_id, product_id, tenant_id, data)
    return VariantInclusionResponse.model_validate(inc)


@router.delete(
    "/admin/products/{product_id}/variants/{variant_id}/inclusions/{inclusion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete variant inclusion",
    dependencies=_delete_deps,
)
async def delete_variant_inclusion(
    product_id: UUID,
    variant_id: UUID,
    inclusion_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = VariantInclusionService(db)
    await svc.delete(inclusion_id, variant_id, product_id, tenant_id)


# ============================================================================
# Variant Images
# ============================================================================


@router.get(
    "/admin/products/{product_id}/variants/{variant_id}/images",
    response_model=list[VariantImageResponse],
    summary="List variant images",
    dependencies=_read_deps,
)
async def list_variant_images(
    product_id: UUID,
    variant_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[VariantImageResponse]:
    svc = VariantImageService(db)
    images = await svc.list_images(variant_id, product_id, tenant_id)
    return [VariantImageResponse.model_validate(img) for img in images]


@router.post(
    "/admin/products/{product_id}/variants/{variant_id}/images",
    response_model=VariantImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload variant image",
    dependencies=_create_deps,
)
async def upload_variant_image(
    product_id: UUID,
    variant_id: UUID,
    file: UploadFile = File(...),
    alt: str | None = Form(default=None),
    is_cover: bool = Form(default=False),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> VariantImageResponse:
    svc = VariantImageService(db)
    image = await svc.upload_image(variant_id, product_id, tenant_id, file, alt, is_cover)
    return VariantImageResponse.model_validate(image)


@router.delete(
    "/admin/products/{product_id}/variants/{variant_id}/images/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete variant image",
    dependencies=_delete_deps,
)
async def delete_variant_image(
    product_id: UUID,
    variant_id: UUID,
    image_id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = VariantImageService(db)
    await svc.delete_image(image_id, variant_id, product_id, tenant_id)
