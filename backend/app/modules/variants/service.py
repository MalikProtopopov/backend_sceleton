"""Variant module service layer."""

import itertools
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.media.upload_service import image_upload_service
from app.modules.catalog.models import Product, ProductPrice
from app.modules.variants.models import (
    ProductOptionGroup,
    ProductOptionValue,
    ProductVariant,
    VariantImage,
    VariantInclusion,
    VariantOptionLink,
    VariantPrice,
)
from app.modules.variants.schemas import (
    OptionGroupCreate,
    OptionGroupUpdate,
    OptionValueCreate,
    OptionValueUpdate,
    VariantCreate,
    VariantInclusionCreate,
    VariantInclusionUpdate,
    VariantPriceCreate,
    VariantPriceUpdate,
    VariantUpdate,
)


async def _get_product(db: AsyncSession, product_id: UUID, tenant_id: UUID) -> Product:
    stmt = select(Product).where(
        Product.id == product_id,
        Product.tenant_id == tenant_id,
        Product.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError("Product", product_id)
    return product


async def update_product_price_range(db: AsyncSession, product_id: UUID) -> None:
    """Recalculate denormalized price_from/price_to from variant prices."""
    sub = (
        select(
            func.min(VariantPrice.amount).label("min_p"),
            func.max(VariantPrice.amount).label("max_p"),
        )
        .join(ProductVariant, VariantPrice.variant_id == ProductVariant.id)
        .where(
            ProductVariant.product_id == product_id,
            ProductVariant.deleted_at.is_(None),
            ProductVariant.is_active.is_(True),
            VariantPrice.price_type == "regular",
            or_(VariantPrice.valid_from.is_(None), VariantPrice.valid_from <= func.current_date()),
            or_(VariantPrice.valid_to.is_(None), VariantPrice.valid_to >= func.current_date()),
        )
    )
    row = (await db.execute(sub)).one_or_none()

    if row and row.min_p is not None:
        price_from, price_to = row.min_p, row.max_p
    else:
        # Fallback to ProductPrice for non-variant products
        pp_sub = (
            select(
                func.min(ProductPrice.amount).label("min_p"),
                func.max(ProductPrice.amount).label("max_p"),
            )
            .where(
                ProductPrice.product_id == product_id,
                ProductPrice.price_type == "regular",
                or_(ProductPrice.valid_from.is_(None), ProductPrice.valid_from <= func.current_date()),
                or_(ProductPrice.valid_to.is_(None), ProductPrice.valid_to >= func.current_date()),
            )
        )
        pp_row = (await db.execute(pp_sub)).one_or_none()
        price_from = pp_row.min_p if pp_row else None
        price_to = pp_row.max_p if pp_row else None

    await db.execute(
        update(Product)
        .where(Product.id == product_id)
        .values(price_from=price_from, price_to=price_to)
    )


# ============================================================================
# Option Group Service
# ============================================================================


class OptionGroupService(BaseService[ProductOptionGroup]):
    model = ProductOptionGroup

    async def list_for_product(
        self, product_id: UUID, tenant_id: UUID,
    ) -> list[ProductOptionGroup]:
        await _get_product(self.db, product_id, tenant_id)
        stmt = (
            select(ProductOptionGroup)
            .options(selectinload(ProductOptionGroup.values))
            .where(ProductOptionGroup.product_id == product_id)
            .order_by(ProductOptionGroup.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def create(
        self, product_id: UUID, tenant_id: UUID, data: OptionGroupCreate,
    ) -> ProductOptionGroup:
        await _get_product(self.db, product_id, tenant_id)

        group = ProductOptionGroup(
            id=uuid4(),
            product_id=product_id,
            tenant_id=tenant_id,
            title=data.title,
            slug=data.slug,
            display_type=data.display_type,
            sort_order=data.sort_order,
            is_required=data.is_required,
            parameter_id=data.parameter_id,
        )
        self.db.add(group)
        await self.db.flush()

        for v in data.values:
            val = ProductOptionValue(
                id=uuid4(),
                option_group_id=group.id,
                title=v.title,
                slug=v.slug,
                sort_order=v.sort_order,
                color_hex=v.color_hex,
                image_url=v.image_url,
            )
            self.db.add(val)
        await self.db.flush()
        await self.db.refresh(group, attribute_names=["values"])
        return group

    @transactional
    async def update(
        self, group_id: UUID, product_id: UUID, tenant_id: UUID,
        data: OptionGroupUpdate,
    ) -> ProductOptionGroup:
        group = await self._get_group(group_id, product_id, tenant_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(group, field, value)
        await self.db.flush()
        await self.db.refresh(group, attribute_names=["values"])
        return group

    @transactional
    async def delete(self, group_id: UUID, product_id: UUID, tenant_id: UUID) -> None:
        group = await self._get_group(group_id, product_id, tenant_id)
        await self.db.delete(group)
        await self.db.flush()

    # --- Option Values ---

    @transactional
    async def create_value(
        self, group_id: UUID, product_id: UUID, tenant_id: UUID,
        data: OptionValueCreate,
    ) -> ProductOptionValue:
        await self._get_group(group_id, product_id, tenant_id)
        val = ProductOptionValue(
            id=uuid4(),
            option_group_id=group_id,
            title=data.title,
            slug=data.slug,
            sort_order=data.sort_order,
            color_hex=data.color_hex,
            image_url=data.image_url,
        )
        self.db.add(val)
        await self.db.flush()
        await self.db.refresh(val)
        return val

    @transactional
    async def update_value(
        self, value_id: UUID, group_id: UUID, product_id: UUID, tenant_id: UUID,
        data: OptionValueUpdate,
    ) -> ProductOptionValue:
        await self._get_group(group_id, product_id, tenant_id)
        val = await self._get_value(value_id, group_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(val, field, value)
        await self.db.flush()
        await self.db.refresh(val)
        return val

    @transactional
    async def delete_value(
        self, value_id: UUID, group_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> None:
        await self._get_group(group_id, product_id, tenant_id)
        val = await self._get_value(value_id, group_id)
        await self.db.delete(val)
        await self.db.flush()

    # --- Helpers ---

    async def _get_group(
        self, group_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> ProductOptionGroup:
        stmt = (
            select(ProductOptionGroup)
            .options(selectinload(ProductOptionGroup.values))
            .where(
                ProductOptionGroup.id == group_id,
                ProductOptionGroup.product_id == product_id,
                ProductOptionGroup.tenant_id == tenant_id,
            )
        )
        result = await self.db.execute(stmt)
        group = result.scalar_one_or_none()
        if not group:
            raise NotFoundError("ProductOptionGroup", group_id)
        return group

    async def _get_value(self, value_id: UUID, group_id: UUID) -> ProductOptionValue:
        stmt = select(ProductOptionValue).where(
            ProductOptionValue.id == value_id,
            ProductOptionValue.option_group_id == group_id,
        )
        result = await self.db.execute(stmt)
        val = result.scalar_one_or_none()
        if not val:
            raise NotFoundError("ProductOptionValue", value_id)
        return val


# ============================================================================
# Variant Service
# ============================================================================


class VariantService(BaseService[ProductVariant]):
    model = ProductVariant

    def _eager_options(self) -> list:
        return [
            selectinload(ProductVariant.prices),
            selectinload(ProductVariant.option_links).selectinload(VariantOptionLink.option_value),
            selectinload(ProductVariant.images),
            selectinload(ProductVariant.inclusions),
        ]

    async def list_for_product(
        self, product_id: UUID, tenant_id: UUID,
    ) -> list[ProductVariant]:
        await _get_product(self.db, product_id, tenant_id)
        stmt = (
            select(ProductVariant)
            .options(*self._eager_options())
            .where(
                ProductVariant.product_id == product_id,
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.deleted_at.is_(None),
            )
            .order_by(ProductVariant.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> ProductVariant:
        stmt = (
            select(ProductVariant)
            .options(*self._eager_options())
            .where(
                ProductVariant.id == variant_id,
                ProductVariant.product_id == product_id,
                ProductVariant.tenant_id == tenant_id,
                ProductVariant.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        variant = result.scalar_one_or_none()
        if not variant:
            raise NotFoundError("ProductVariant", variant_id)
        return variant

    @transactional
    async def create(
        self, product_id: UUID, tenant_id: UUID, data: VariantCreate,
    ) -> ProductVariant:
        product = await _get_product(self.db, product_id, tenant_id)

        if not product.has_variants:
            product.has_variants = True

        variant = ProductVariant(
            id=uuid4(),
            product_id=product_id,
            tenant_id=tenant_id,
            sku=data.sku,
            slug=data.slug,
            title=data.title,
            description=data.description,
            is_default=data.is_default,
            is_active=data.is_active,
            sort_order=data.sort_order,
            stock_quantity=data.stock_quantity,
            weight=data.weight,
        )
        self.db.add(variant)

        if data.is_default:
            await self._unset_other_defaults(product_id, variant.id)

        await self.db.flush()

        for ov_id in data.option_value_ids:
            link = VariantOptionLink(id=uuid4(), variant_id=variant.id, option_value_id=ov_id)
            self.db.add(link)
        await self.db.flush()
        await self.db.refresh(variant)
        return variant

    @transactional
    async def update(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
        data: VariantUpdate,
    ) -> ProductVariant:
        variant = await self.get_by_id(variant_id, product_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True, exclude={"option_value_ids"})
        is_active_changed = "is_active" in update_data and update_data["is_active"] != variant.is_active
        for field, value in update_data.items():
            setattr(variant, field, value)

        if data.is_default:
            await self._unset_other_defaults(product_id, variant.id)

        if data.option_value_ids is not None:
            await self.db.execute(
                delete(VariantOptionLink).where(VariantOptionLink.variant_id == variant_id)
            )
            await self.db.flush()
            for ov_id in data.option_value_ids:
                link = VariantOptionLink(id=uuid4(), variant_id=variant.id, option_value_id=ov_id)
                self.db.add(link)

        await self.db.flush()

        if is_active_changed:
            await update_product_price_range(self.db, product_id)

        await self.db.refresh(variant)
        return variant

    @transactional
    async def soft_delete(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> None:
        variant = await self.get_by_id(variant_id, product_id, tenant_id)
        variant.soft_delete()
        await self.db.flush()
        await update_product_price_range(self.db, product_id)

    @transactional
    async def generate_matrix(
        self,
        product_id: UUID,
        tenant_id: UUID,
        option_group_ids: list[UUID],
        base_price: Decimal | None = None,
    ) -> list[ProductVariant]:
        """Generate all variant combinations from the given option groups."""
        product = await _get_product(self.db, product_id, tenant_id)

        groups_stmt = (
            select(ProductOptionGroup)
            .options(selectinload(ProductOptionGroup.values))
            .where(
                ProductOptionGroup.product_id == product_id,
                ProductOptionGroup.id.in_(option_group_ids),
            )
            .order_by(ProductOptionGroup.sort_order)
        )
        groups = list((await self.db.execute(groups_stmt)).scalars().all())

        value_lists = [
            sorted(g.values, key=lambda v: v.sort_order)
            for g in groups
            if g.values
        ]
        if not value_lists:
            return []

        existing_stmt = (
            select(ProductVariant.sku)
            .where(
                ProductVariant.product_id == product_id,
                ProductVariant.deleted_at.is_(None),
            )
        )
        existing_skus = set(
            (await self.db.execute(existing_stmt)).scalars().all()
        )

        created: list[ProductVariant] = []
        for idx, combo in enumerate(itertools.product(*value_lists)):
            parts = [v.slug for v in combo]
            slug = "-".join(parts)
            title = " / ".join(v.title for v in combo)
            sku = f"{product.sku}-{'-'.join(parts).upper()}"

            if sku in existing_skus:
                continue

            variant = ProductVariant(
                id=uuid4(),
                product_id=product_id,
                tenant_id=tenant_id,
                sku=sku,
                slug=slug,
                title=title,
                is_default=(idx == 0 and not existing_skus),
                is_active=False,
                sort_order=idx,
            )
            self.db.add(variant)
            await self.db.flush()

            for ov in combo:
                link = VariantOptionLink(
                    id=uuid4(), variant_id=variant.id, option_value_id=ov.id,
                )
                self.db.add(link)

            if base_price is not None:
                price = VariantPrice(
                    id=uuid4(),
                    variant_id=variant.id,
                    price_type="regular",
                    amount=base_price,
                )
                self.db.add(price)

            created.append(variant)
            existing_skus.add(sku)

        await self.db.flush()

        if not product.has_variants:
            product.has_variants = True
            await self.db.flush()

        if base_price is not None and created:
            await update_product_price_range(self.db, product_id)

        return created

    async def _unset_other_defaults(self, product_id: UUID, keep_id: UUID) -> None:
        await self.db.execute(
            update(ProductVariant)
            .where(
                ProductVariant.product_id == product_id,
                ProductVariant.id != keep_id,
                ProductVariant.is_default.is_(True),
            )
            .values(is_default=False)
        )


# ============================================================================
# Variant Price Service
# ============================================================================


class VariantPriceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._variant_svc = VariantService(db)

    async def list_prices(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> list[VariantPrice]:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        stmt = (
            select(VariantPrice)
            .where(VariantPrice.variant_id == variant_id)
            .order_by(VariantPrice.price_type, VariantPrice.valid_from.desc().nulls_last())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    @transactional
    async def create_price(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
        data: VariantPriceCreate,
    ) -> VariantPrice:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        price = VariantPrice(
            id=uuid4(),
            variant_id=variant_id,
            price_type=data.price_type,
            amount=data.amount,
            currency=data.currency,
            valid_from=data.valid_from,
            valid_to=data.valid_to,
        )
        self.db.add(price)
        await self.db.flush()
        await update_product_price_range(self.db, product_id)
        await self.db.refresh(price)
        return price

    @transactional
    async def update_price(
        self, price_id: UUID, variant_id: UUID, product_id: UUID, tenant_id: UUID,
        data: VariantPriceUpdate,
    ) -> VariantPrice:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        stmt = select(VariantPrice).where(
            VariantPrice.id == price_id, VariantPrice.variant_id == variant_id,
        )
        price = (await self.db.execute(stmt)).scalar_one_or_none()
        if not price:
            raise NotFoundError("VariantPrice", price_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(price, field, value)
        await self.db.flush()
        await update_product_price_range(self.db, product_id)
        await self.db.refresh(price)
        return price

    @transactional
    async def delete_price(
        self, price_id: UUID, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> None:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        stmt = select(VariantPrice).where(
            VariantPrice.id == price_id, VariantPrice.variant_id == variant_id,
        )
        price = (await self.db.execute(stmt)).scalar_one_or_none()
        if not price:
            raise NotFoundError("VariantPrice", price_id)
        await self.db.delete(price)
        await self.db.flush()
        await update_product_price_range(self.db, product_id)


# ============================================================================
# Variant Inclusion Service
# ============================================================================


class VariantInclusionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._variant_svc = VariantService(db)

    async def list_inclusions(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> list[VariantInclusion]:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        stmt = (
            select(VariantInclusion)
            .where(VariantInclusion.variant_id == variant_id)
            .order_by(VariantInclusion.sort_order)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    @transactional
    async def create(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
        data: VariantInclusionCreate,
    ) -> VariantInclusion:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        inc = VariantInclusion(
            id=uuid4(),
            variant_id=variant_id,
            title=data.title,
            description=data.description,
            is_included=data.is_included,
            sort_order=data.sort_order,
            icon=data.icon,
            group=data.group,
        )
        self.db.add(inc)
        await self.db.flush()
        await self.db.refresh(inc)
        return inc

    @transactional
    async def update(
        self, inclusion_id: UUID, variant_id: UUID, product_id: UUID, tenant_id: UUID,
        data: VariantInclusionUpdate,
    ) -> VariantInclusion:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        inc = await self._get(inclusion_id, variant_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(inc, field, value)
        await self.db.flush()
        await self.db.refresh(inc)
        return inc

    @transactional
    async def delete(
        self, inclusion_id: UUID, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> None:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        inc = await self._get(inclusion_id, variant_id)
        await self.db.delete(inc)
        await self.db.flush()

    async def _get(self, inclusion_id: UUID, variant_id: UUID) -> VariantInclusion:
        stmt = select(VariantInclusion).where(
            VariantInclusion.id == inclusion_id,
            VariantInclusion.variant_id == variant_id,
        )
        inc = (await self.db.execute(stmt)).scalar_one_or_none()
        if not inc:
            raise NotFoundError("VariantInclusion", inclusion_id)
        return inc


# ============================================================================
# Variant Image Service
# ============================================================================


class VariantImageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._variant_svc = VariantService(db)

    async def list_images(
        self, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> list[VariantImage]:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        stmt = (
            select(VariantImage)
            .where(VariantImage.variant_id == variant_id)
            .order_by(VariantImage.sort_order)
        )
        return list((await self.db.execute(stmt)).scalars().all())

    @transactional
    async def upload_image(
        self,
        variant_id: UUID,
        product_id: UUID,
        tenant_id: UUID,
        file,
        alt: str | None = None,
        is_cover: bool = False,
    ) -> VariantImage:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)

        url = await image_upload_service.upload_image(
            file=file,
            tenant_id=tenant_id,
            folder="variants",
            entity_id=variant_id,
        )
        storage_key = image_upload_service._extract_s3_key_from_url(url) or ""

        if is_cover:
            await self.db.execute(
                update(VariantImage)
                .where(VariantImage.variant_id == variant_id)
                .values(is_cover=False)
            )

        max_order = (
            await self.db.execute(
                select(func.max(VariantImage.sort_order))
                .where(VariantImage.variant_id == variant_id)
            )
        ).scalar() or 0

        image = VariantImage(
            id=uuid4(),
            variant_id=variant_id,
            storage_key=storage_key,
            url=url,
            alt=alt,
            mime_type=file.content_type,
            size_bytes=file.size,
            sort_order=max_order + 1,
            is_cover=is_cover,
        )
        self.db.add(image)
        await self.db.flush()
        await self.db.refresh(image)
        return image

    @transactional
    async def delete_image(
        self, image_id: UUID, variant_id: UUID, product_id: UUID, tenant_id: UUID,
    ) -> None:
        await self._variant_svc.get_by_id(variant_id, product_id, tenant_id)
        stmt = select(VariantImage).where(
            VariantImage.id == image_id, VariantImage.variant_id == variant_id,
        )
        image = (await self.db.execute(stmt)).scalar_one_or_none()
        if not image:
            raise NotFoundError("VariantImage", image_id)
        await image_upload_service.delete_image(image.url)
        await self.db.delete(image)
        await self.db.flush()
