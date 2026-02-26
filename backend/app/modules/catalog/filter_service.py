"""Faceted filtering service for product catalog.

Provides:
- Faceted filter list with counts (auto-excluding own facet)
- Product filtering by parameter slug/value slugs
- Price range filtering and sorting
- Multi-category filtering via slugs
- Product characteristic serialisation for public API
"""

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, and_, case, distinct, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalog.models import (
    Category,
    Product,
    ProductCategory,
    ProductPrice,
)
from app.modules.catalog.schemas import (
    CharacteristicValuePublic,
    FilterParameterResponse,
    FilterValueResponse,
    FiltersResponse,
    PriceRangeResponse,
    ProductCharacteristicPublicResponse,
    ProductCharPublicResponse,
    UOMPublicResponse,
)
from app.modules.parameters.models import (
    Parameter,
    ParameterCategory,
    ParameterValue,
    ProductCharacteristic,
)


class CatalogFilterService:
    """Service for faceted navigation and catalog filtering."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Resolve category slugs -> IDs
    # ------------------------------------------------------------------

    async def _resolve_category_ids(
        self, tenant_id: UUID, category_slugs: list[str],
    ) -> list[UUID]:
        if not category_slugs:
            return []
        stmt = (
            select(Category.id)
            .where(
                Category.tenant_id == tenant_id,
                Category.slug.in_(category_slugs),
                Category.is_active.is_(True),
                Category.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Resolve parameter slug -> value slugs -> value IDs
    # ------------------------------------------------------------------

    async def _resolve_filter_params(
        self, tenant_id: UUID, raw_filters: dict[str, list[str]],
    ) -> dict[UUID, list[UUID]]:
        """Convert {param_slug: [value_slug, ...]} to {parameter_id: [value_id, ...]}."""
        if not raw_filters:
            return {}

        param_slugs = list(raw_filters.keys())
        stmt = (
            select(Parameter)
            .where(
                Parameter.tenant_id == tenant_id,
                Parameter.slug.in_(param_slugs),
                Parameter.is_active.is_(True),
                Parameter.is_filterable.is_(True),
            )
            .options(selectinload(Parameter.values))
        )
        result = await self.db.execute(stmt)
        params = result.scalars().all()

        resolved: dict[UUID, list[UUID]] = {}
        for param in params:
            value_slugs = raw_filters.get(param.slug, [])
            if not value_slugs:
                continue
            value_ids = [
                v.id for v in param.values
                if v.slug in value_slugs and v.is_active
            ]
            if value_ids:
                resolved[param.id] = value_ids

        return resolved

    # ------------------------------------------------------------------
    # Base product query (active, non-deleted, tenant-scoped)
    # ------------------------------------------------------------------

    def _base_product_query(self, tenant_id: UUID):
        return (
            select(Product.id)
            .where(
                Product.tenant_id == tenant_id,
                Product.is_active.is_(True),
                Product.deleted_at.is_(None),
            )
        )

    def _apply_category_filter(self, q, category_ids: list[UUID]):
        if not category_ids:
            return q
        return q.where(
            Product.id.in_(
                select(ProductCategory.product_id).where(
                    ProductCategory.category_id.in_(category_ids)
                )
            )
        )

    def _apply_param_filters(
        self, q, param_filters: dict[UUID, list[UUID]], exclude_param_id: UUID | None = None,
    ):
        """Add EXISTS subqueries for each parameter filter (AND logic between params)."""
        for param_id, value_ids in param_filters.items():
            if param_id == exclude_param_id:
                continue
            sub = (
                select(literal(1))
                .where(
                    ProductCharacteristic.product_id == Product.id,
                    ProductCharacteristic.parameter_id == param_id,
                    ProductCharacteristic.parameter_value_id.in_(value_ids),
                )
            )
            q = q.where(sub.exists())
        return q

    def _apply_price_filter(self, q, price_min: Decimal | None, price_max: Decimal | None):
        if price_min is None and price_max is None:
            return q
        price_sub = (
            select(ProductPrice.product_id)
            .where(
                ProductPrice.price_type == "regular",
                or_(ProductPrice.valid_from.is_(None), ProductPrice.valid_from <= func.current_date()),
                or_(ProductPrice.valid_to.is_(None), ProductPrice.valid_to >= func.current_date()),
            )
        )
        if price_min is not None:
            price_sub = price_sub.where(ProductPrice.amount >= price_min)
        if price_max is not None:
            price_sub = price_sub.where(ProductPrice.amount <= price_max)
        return q.where(Product.id.in_(price_sub))

    # ------------------------------------------------------------------
    # GET /public/filters
    # ------------------------------------------------------------------

    async def get_filters(
        self,
        tenant_id: UUID,
        category_slugs: list[str] | None = None,
        active_filters: dict[str, list[str]] | None = None,
        price_min: Decimal | None = None,
        price_max: Decimal | None = None,
    ) -> FiltersResponse:
        category_ids = await self._resolve_category_ids(tenant_id, category_slugs or [])
        param_filters = await self._resolve_filter_params(tenant_id, active_filters or {})

        # Get filterable parameters (scoped to categories if provided)
        param_query = (
            select(Parameter)
            .where(
                Parameter.tenant_id == tenant_id,
                Parameter.is_active.is_(True),
                Parameter.is_filterable.is_(True),
            )
            .options(selectinload(Parameter.values))
        )
        if category_ids:
            param_query = param_query.where(
                or_(
                    Parameter.scope == "global",
                    Parameter.id.in_(
                        select(ParameterCategory.parameter_id).where(
                            ParameterCategory.category_id.in_(category_ids)
                        )
                    ),
                )
            )
        param_query = param_query.order_by(Parameter.sort_order, Parameter.name)
        params_result = await self.db.execute(param_query)
        parameters = list(params_result.scalars().unique().all())

        # Build filter response for each parameter
        filter_responses: list[FilterParameterResponse] = []
        for param in parameters:
            if param.value_type in ("enum",):
                values = await self._count_enum_values(
                    tenant_id, param, category_ids, param_filters, price_min, price_max,
                )
                if not values:
                    continue
                uom_resp = None
                if param.uom:
                    uom_resp = UOMPublicResponse(code=param.uom.code, symbol=param.uom.symbol)
                filter_responses.append(FilterParameterResponse(
                    slug=param.slug,
                    name=param.name,
                    type=param.value_type,
                    values=values,
                    uom=uom_resp,
                ))
            elif param.value_type in ("number", "range"):
                min_val, max_val = await self._range_bounds(
                    tenant_id, param.id, category_ids, param_filters, price_min, price_max,
                )
                if min_val is None and max_val is None:
                    continue
                uom_resp = None
                if param.uom:
                    uom_resp = UOMPublicResponse(code=param.uom.code, symbol=param.uom.symbol)
                filter_responses.append(FilterParameterResponse(
                    slug=param.slug,
                    name=param.name,
                    type=param.value_type,
                    uom=uom_resp,
                    min=min_val,
                    max=max_val,
                ))

        # Price range
        price_range = await self._get_price_range(
            tenant_id, category_ids, param_filters, price_min, price_max,
        )

        # Total products count
        total_q = self._base_product_query(tenant_id)
        total_q = self._apply_category_filter(total_q, category_ids)
        total_q = self._apply_param_filters(total_q, param_filters)
        total_q = self._apply_price_filter(total_q, price_min, price_max)
        count_stmt = select(func.count(distinct(Product.id))).select_from(
            total_q.subquery()
        )
        total_products = (await self.db.execute(count_stmt)).scalar() or 0

        return FiltersResponse(
            filters=filter_responses,
            price_range=price_range,
            total_products=total_products,
        )

    async def _count_enum_values(
        self,
        tenant_id: UUID,
        param: Parameter,
        category_ids: list[UUID],
        param_filters: dict[UUID, list[UUID]],
        price_min: Decimal | None,
        price_max: Decimal | None,
    ) -> list[FilterValueResponse]:
        """Count products for each enum value, excluding own facet from filters."""
        active_values = [v for v in param.values if v.is_active]
        if not active_values:
            return []

        # Base: products matching ALL OTHER filters (not this parameter's)
        base_q = self._base_product_query(tenant_id)
        base_q = self._apply_category_filter(base_q, category_ids)
        base_q = self._apply_param_filters(base_q, param_filters, exclude_param_id=param.id)
        base_q = self._apply_price_filter(base_q, price_min, price_max)

        product_ids_sub = base_q.subquery()

        stmt = (
            select(
                ProductCharacteristic.parameter_value_id,
                func.count(distinct(ProductCharacteristic.product_id)),
            )
            .where(
                ProductCharacteristic.parameter_id == param.id,
                ProductCharacteristic.parameter_value_id.isnot(None),
                ProductCharacteristic.product_id.in_(select(product_ids_sub.c.id)),
            )
            .group_by(ProductCharacteristic.parameter_value_id)
        )
        result = await self.db.execute(stmt)
        counts: dict[UUID, int] = {row[0]: row[1] for row in result.all()}

        values = []
        for v in active_values:
            count = counts.get(v.id, 0)
            if count > 0:
                values.append(FilterValueResponse(slug=v.slug, label=v.label, count=count))

        return values

    async def _range_bounds(
        self,
        tenant_id: UUID,
        parameter_id: UUID,
        category_ids: list[UUID],
        param_filters: dict[UUID, list[UUID]],
        price_min: Decimal | None,
        price_max: Decimal | None,
    ) -> tuple[Decimal | None, Decimal | None]:
        base_q = self._base_product_query(tenant_id)
        base_q = self._apply_category_filter(base_q, category_ids)
        base_q = self._apply_param_filters(base_q, param_filters, exclude_param_id=parameter_id)
        base_q = self._apply_price_filter(base_q, price_min, price_max)
        product_ids_sub = base_q.subquery()

        stmt = (
            select(
                func.min(ProductCharacteristic.value_number),
                func.max(ProductCharacteristic.value_number),
            )
            .where(
                ProductCharacteristic.parameter_id == parameter_id,
                ProductCharacteristic.value_number.isnot(None),
                ProductCharacteristic.product_id.in_(select(product_ids_sub.c.id)),
            )
        )
        result = await self.db.execute(stmt)
        row = result.one_or_none()
        if row:
            return row[0], row[1]
        return None, None

    async def _get_price_range(
        self,
        tenant_id: UUID,
        category_ids: list[UUID],
        param_filters: dict[UUID, list[UUID]],
        price_min: Decimal | None,
        price_max: Decimal | None,
    ) -> PriceRangeResponse:
        base_q = self._base_product_query(tenant_id)
        base_q = self._apply_category_filter(base_q, category_ids)
        base_q = self._apply_param_filters(base_q, param_filters)
        product_ids_sub = base_q.subquery()

        stmt = (
            select(
                func.min(ProductPrice.amount),
                func.max(ProductPrice.amount),
            )
            .where(
                ProductPrice.price_type == "regular",
                or_(ProductPrice.valid_from.is_(None), ProductPrice.valid_from <= func.current_date()),
                or_(ProductPrice.valid_to.is_(None), ProductPrice.valid_to >= func.current_date()),
                ProductPrice.product_id.in_(select(product_ids_sub.c.id)),
            )
        )
        result = await self.db.execute(stmt)
        row = result.one_or_none()
        if row and row[0] is not None:
            return PriceRangeResponse(min=row[0], max=row[1])
        return PriceRangeResponse()

    # ------------------------------------------------------------------
    # Product listing with filters + sorting
    # ------------------------------------------------------------------

    async def list_products_filtered(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        brand: str | None = None,
        category_slugs: list[str] | None = None,
        param_filters_raw: dict[str, list[str]] | None = None,
        price_min: Decimal | None = None,
        price_max: Decimal | None = None,
        sort: str = "newest",
    ) -> tuple[list[Product], int]:
        from app.modules.catalog.models import ProductImage

        category_ids = await self._resolve_category_ids(tenant_id, category_slugs or [])
        param_filters = await self._resolve_filter_params(tenant_id, param_filters_raw or {})

        q = (
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.is_active.is_(True),
                Product.deleted_at.is_(None),
            )
        )

        if search:
            pattern = f"%{search}%"
            q = q.where(
                or_(
                    Product.title.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.brand.ilike(pattern),
                )
            )

        if brand:
            q = q.where(Product.brand.ilike(f"%{brand}%"))

        if category_ids:
            q = q.where(
                Product.id.in_(
                    select(ProductCategory.product_id).where(
                        ProductCategory.category_id.in_(category_ids)
                    )
                )
            )

        for param_id, value_ids in param_filters.items():
            sub = (
                select(literal(1))
                .where(
                    ProductCharacteristic.product_id == Product.id,
                    ProductCharacteristic.parameter_id == param_id,
                    ProductCharacteristic.parameter_value_id.in_(value_ids),
                )
            )
            q = q.where(sub.exists())

        if price_min is not None or price_max is not None:
            price_sub = (
                select(ProductPrice.product_id)
                .where(
                    ProductPrice.price_type == "regular",
                    or_(ProductPrice.valid_from.is_(None), ProductPrice.valid_from <= func.current_date()),
                    or_(ProductPrice.valid_to.is_(None), ProductPrice.valid_to >= func.current_date()),
                )
            )
            if price_min is not None:
                price_sub = price_sub.where(ProductPrice.amount >= price_min)
            if price_max is not None:
                price_sub = price_sub.where(ProductPrice.amount <= price_max)
            q = q.where(Product.id.in_(price_sub))

        # Sorting
        if sort in ("price_asc", "price_desc"):
            current_price_sub = (
                select(func.min(ProductPrice.amount))
                .where(
                    ProductPrice.product_id == Product.id,
                    ProductPrice.price_type == "regular",
                    or_(ProductPrice.valid_from.is_(None), ProductPrice.valid_from <= func.current_date()),
                    or_(ProductPrice.valid_to.is_(None), ProductPrice.valid_to >= func.current_date()),
                )
                .correlate(Product)
                .scalar_subquery()
                .label("current_price")
            )
            q = q.add_columns(current_price_sub)
            if sort == "price_asc":
                q = q.order_by(current_price_sub.asc().nullslast())
            else:
                q = q.order_by(current_price_sub.desc().nullslast())
        elif sort == "title_asc":
            q = q.order_by(Product.title.asc())
        elif sort == "title_desc":
            q = q.order_by(Product.title.desc())
        else:
            q = q.order_by(Product.created_at.desc())

        # Count
        base_for_count = select(Product.id).where(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.deleted_at.is_(None),
        )
        if search:
            pattern = f"%{search}%"
            base_for_count = base_for_count.where(
                or_(Product.title.ilike(pattern), Product.sku.ilike(pattern), Product.brand.ilike(pattern))
            )
        if brand:
            base_for_count = base_for_count.where(Product.brand.ilike(f"%{brand}%"))
        if category_ids:
            base_for_count = base_for_count.where(
                Product.id.in_(select(ProductCategory.product_id).where(ProductCategory.category_id.in_(category_ids)))
            )
        for param_id, value_ids in param_filters.items():
            sub = select(literal(1)).where(
                ProductCharacteristic.product_id == Product.id,
                ProductCharacteristic.parameter_id == param_id,
                ProductCharacteristic.parameter_value_id.in_(value_ids),
            )
            base_for_count = base_for_count.where(sub.exists())
        if price_min is not None or price_max is not None:
            price_sub2 = select(ProductPrice.product_id).where(
                ProductPrice.price_type == "regular",
                or_(ProductPrice.valid_from.is_(None), ProductPrice.valid_from <= func.current_date()),
                or_(ProductPrice.valid_to.is_(None), ProductPrice.valid_to >= func.current_date()),
            )
            if price_min is not None:
                price_sub2 = price_sub2.where(ProductPrice.amount >= price_min)
            if price_max is not None:
                price_sub2 = price_sub2.where(ProductPrice.amount <= price_max)
            base_for_count = base_for_count.where(Product.id.in_(price_sub2))

        count_stmt = select(func.count()).select_from(base_for_count.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        page_size = min(page_size, 100)
        page = max(page, 1)
        q = q.options(selectinload(Product.images))
        q = q.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(q)
        rows = result.all()
        # Rows may be (Product,) or (Product, price) depending on sort
        products = []
        for row in rows:
            if isinstance(row, Product):
                products.append(row)
            else:
                products.append(row[0])

        return products, total

    # ------------------------------------------------------------------
    # Product characteristics for public detail page
    # ------------------------------------------------------------------

    async def get_product_characteristics_public(
        self, product_id: UUID,
    ) -> tuple[list[ProductCharacteristicPublicResponse], list[ProductCharPublicResponse]]:
        """Return normalized characteristics and backward-compatible chars."""
        stmt = (
            select(ProductCharacteristic)
            .where(ProductCharacteristic.product_id == product_id)
            .options(
                selectinload(ProductCharacteristic.parameter).selectinload(Parameter.uom),
                selectinload(ProductCharacteristic.parameter_value),
            )
            .order_by(ProductCharacteristic.created_at)
        )
        result = await self.db.execute(stmt)
        chars_db = list(result.scalars().all())

        # Group by parameter
        grouped: dict[UUID, list[ProductCharacteristic]] = defaultdict(list)
        for c in chars_db:
            grouped[c.parameter_id].append(c)

        characteristics: list[ProductCharacteristicPublicResponse] = []
        chars_compat: list[ProductCharPublicResponse] = []

        for param_id, group in grouped.items():
            first = group[0]
            param = first.parameter
            if not param or not param.is_active:
                continue

            uom_resp = None
            char_uom = first.uom_id or (param.uom.id if param.uom else None)
            if param.uom:
                uom_resp = UOMPublicResponse(code=param.uom.code, symbol=param.uom.symbol)

            if param.value_type == "enum":
                values = []
                labels = []
                for c in group:
                    if c.parameter_value and c.parameter_value.is_active:
                        values.append(CharacteristicValuePublic(
                            slug=c.parameter_value.slug,
                            label=c.parameter_value.label,
                        ))
                        labels.append(c.parameter_value.label)
                characteristics.append(ProductCharacteristicPublicResponse(
                    parameter_slug=param.slug,
                    parameter_name=param.name,
                    type=param.value_type,
                    values=values,
                    uom=uom_resp,
                ))
                if labels:
                    chars_compat.append(ProductCharPublicResponse(
                        name=param.name,
                        value_text=", ".join(labels),
                    ))
            else:
                value_text = first.value_text
                if first.value_number is not None:
                    formatted = str(first.value_number)
                    if param.uom:
                        formatted += f" {param.uom.symbol or param.uom.code}"
                    value_text = value_text or formatted

                characteristics.append(ProductCharacteristicPublicResponse(
                    parameter_slug=param.slug,
                    parameter_name=param.name,
                    type=param.value_type,
                    value_text=first.value_text,
                    value_number=first.value_number,
                    value_bool=first.value_bool,
                    uom=uom_resp,
                ))
                if value_text:
                    chars_compat.append(ProductCharPublicResponse(
                        name=param.name,
                        value_text=value_text,
                    ))

        return characteristics, chars_compat

    # ------------------------------------------------------------------
    # SEO: filter page combinations
    # ------------------------------------------------------------------

    async def get_seo_filter_pages(
        self,
        tenant_id: UUID,
        category_slug: str | None = None,
        min_products: int = 1,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[dict], int]:
        """Generate SEO-friendly filter page combinations."""
        category_ids = []
        if category_slug:
            category_ids = await self._resolve_category_ids(tenant_id, [category_slug])
            if not category_ids:
                return [], 0

        # Get all filterable parameters with their values
        param_query = (
            select(Parameter)
            .where(
                Parameter.tenant_id == tenant_id,
                Parameter.is_active.is_(True),
                Parameter.is_filterable.is_(True),
                Parameter.value_type == "enum",
            )
            .options(selectinload(Parameter.values))
            .order_by(Parameter.sort_order)
        )
        if category_ids:
            param_query = param_query.where(
                or_(
                    Parameter.scope == "global",
                    Parameter.id.in_(
                        select(ParameterCategory.parameter_id).where(
                            ParameterCategory.category_id.in_(category_ids)
                        )
                    ),
                )
            )
        params_result = await self.db.execute(param_query)
        parameters = list(params_result.scalars().unique().all())

        # Get categories for URL generation
        cat_slug = category_slug

        pages = []

        # Single-filter pages
        for param in parameters:
            active_values = [v for v in param.values if v.is_active]
            for value in active_values:
                base_q = self._base_product_query(tenant_id)
                base_q = self._apply_category_filter(base_q, category_ids)
                sub = select(literal(1)).where(
                    ProductCharacteristic.product_id == Product.id,
                    ProductCharacteristic.parameter_id == param.id,
                    ProductCharacteristic.parameter_value_id == value.id,
                )
                base_q = base_q.where(sub.exists())
                count_stmt = select(func.count()).select_from(base_q.subquery())
                count = (await self.db.execute(count_stmt)).scalar() or 0

                if count >= min_products:
                    url_parts = []
                    if cat_slug:
                        url_parts.append(f"/catalog/{cat_slug}")
                    else:
                        url_parts.append("/catalog")
                    url_parts.append(f"/{param.slug}--{value.slug}")
                    pages.append({
                        "category_slug": cat_slug,
                        "filters": [{"parameter_slug": param.slug, "value_slug": value.slug}],
                        "product_count": count,
                        "url_path": "".join(url_parts),
                    })

        # Two-filter combination pages
        for i, param1 in enumerate(parameters):
            for param2 in parameters[i + 1:]:
                active1 = [v for v in param1.values if v.is_active]
                active2 = [v for v in param2.values if v.is_active]
                for v1 in active1:
                    for v2 in active2:
                        base_q = self._base_product_query(tenant_id)
                        base_q = self._apply_category_filter(base_q, category_ids)
                        sub1 = select(literal(1)).where(
                            ProductCharacteristic.product_id == Product.id,
                            ProductCharacteristic.parameter_id == param1.id,
                            ProductCharacteristic.parameter_value_id == v1.id,
                        )
                        sub2 = select(literal(1)).where(
                            ProductCharacteristic.product_id == Product.id,
                            ProductCharacteristic.parameter_id == param2.id,
                            ProductCharacteristic.parameter_value_id == v2.id,
                        )
                        base_q = base_q.where(sub1.exists(), sub2.exists())
                        count_stmt = select(func.count()).select_from(base_q.subquery())
                        count = (await self.db.execute(count_stmt)).scalar() or 0

                        if count >= min_products:
                            url_parts = []
                            if cat_slug:
                                url_parts.append(f"/catalog/{cat_slug}")
                            else:
                                url_parts.append("/catalog")
                            url_parts.append(f"/{param1.slug}--{v1.slug}/{param2.slug}--{v2.slug}")
                            pages.append({
                                "category_slug": cat_slug,
                                "filters": [
                                    {"parameter_slug": param1.slug, "value_slug": v1.slug},
                                    {"parameter_slug": param2.slug, "value_slug": v2.slug},
                                ],
                                "product_count": count,
                                "url_path": "".join(url_parts),
                            })

        pages.sort(key=lambda p: p["product_count"], reverse=True)
        total = len(pages)

        start = (page - 1) * page_size
        end = start + page_size
        return pages[start:end], total
