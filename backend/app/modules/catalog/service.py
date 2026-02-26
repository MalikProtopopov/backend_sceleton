"""Catalog module service layer."""

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.core.image_upload import image_upload_service
from app.core.pagination import paginate_query
from app.modules.catalog.models import (
    Category,
    Product,
    ProductAlias,
    ProductAnalog,
    ProductCategory,
    ProductImage,
    ProductPrice,
    UOM,
)
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryUpdate,
    ProductAliasCreate,
    ProductAnalogCreate,
    ProductCreate,
    ProductPriceCreate,
    ProductPriceUpdate,
    ProductUpdate,
)


# ============================================================================
# UOM Service
# ============================================================================


class UOMService(BaseService[UOM]):
    """Service for units of measure."""

    model = UOM

    async def get_by_id(self, uom_id: UUID, tenant_id: UUID) -> UOM:
        return await self._get_by_id(uom_id, tenant_id)

    async def list_all(self, tenant_id: UUID, active_only: bool = True) -> list[UOM]:
        filters = []
        if active_only:
            filters.append(UOM.is_active.is_(True))
        return await self._list_all(tenant_id, filters=filters)

    @transactional
    async def create(self, tenant_id: UUID, name: str, code: str, symbol: str | None = None) -> UOM:
        stmt = select(UOM).where(UOM.tenant_id == tenant_id, UOM.code == code)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise AlreadyExistsError("UOM", "code", code)

        uom = UOM(tenant_id=tenant_id, name=name, code=code, symbol=symbol)
        self.db.add(uom)
        await self.db.flush()
        await self.db.refresh(uom)
        return uom

    @transactional
    async def update(self, uom_id: UUID, tenant_id: UUID, **data) -> UOM:
        uom = await self.get_by_id(uom_id, tenant_id)
        for field, value in data.items():
            if hasattr(uom, field):
                setattr(uom, field, value)
        await self.db.flush()
        await self.db.refresh(uom)
        return uom

    @transactional
    async def deactivate(self, uom_id: UUID, tenant_id: UUID) -> None:
        uom = await self.get_by_id(uom_id, tenant_id)
        uom.is_active = False
        await self.db.flush()


# ============================================================================
# Category Service
# ============================================================================


class CategoryService(BaseService[Category]):
    """Service for hierarchical product categories."""

    model = Category

    async def get_by_id(self, category_id: UUID, tenant_id: UUID) -> Category:
        return await self._get_by_id(category_id, tenant_id)

    async def list_categories(
        self,
        tenant_id: UUID,
        parent_id: UUID | None = None,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Category], int]:
        filters = []
        if active_only:
            filters.append(Category.is_active.is_(True))
        if parent_id is not None:
            filters.append(Category.parent_id == parent_id)
        else:
            filters.append(Category.parent_id.is_(None))

        base_query = self._build_base_query(tenant_id, filters=filters)
        return await paginate_query(
            self.db, base_query, page, page_size,
            order_by=[Category.sort_order, Category.title],
        )

    async def list_tree(self, tenant_id: UUID, active_only: bool = True) -> list[Category]:
        """Flat list of all categories; client builds tree from parent_id."""
        filters = []
        if active_only:
            filters.append(Category.is_active.is_(True))
        return await self._list_all(
            tenant_id, filters=filters,
            order_by=[Category.sort_order, Category.title],
        )

    @transactional
    async def create(self, tenant_id: UUID, data: CategoryCreate) -> Category:
        stmt = select(Category).where(
            Category.tenant_id == tenant_id, Category.slug == data.slug,
            Category.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise AlreadyExistsError("Category", "slug", data.slug)

        if data.parent_id:
            await self.get_by_id(data.parent_id, tenant_id)

        category = Category(tenant_id=tenant_id, **data.model_dump())
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    @transactional
    async def update(self, category_id: UUID, tenant_id: UUID, data: CategoryUpdate) -> Category:
        category = await self.get_by_id(category_id, tenant_id)
        category.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        if "slug" in update_data and update_data["slug"] != category.slug:
            stmt = select(Category).where(
                Category.tenant_id == tenant_id,
                Category.slug == update_data["slug"],
                Category.id != category_id,
                Category.deleted_at.is_(None),
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                raise AlreadyExistsError("Category", "slug", update_data["slug"])

        for field, value in update_data.items():
            setattr(category, field, value)

        await self.db.flush()
        await self.db.refresh(category)
        return category

    @transactional
    async def soft_delete(self, category_id: UUID, tenant_id: UUID) -> None:
        await self._soft_delete(category_id, tenant_id)

    # ========== Public methods ==========

    async def list_public(self, tenant_id: UUID) -> list[Category]:
        """All active categories for public display (client builds tree from parent_id)."""
        filters = [
            Category.is_active.is_(True),
        ]
        return await self._list_all(
            tenant_id, filters=filters,
            order_by=[Category.sort_order, Category.title],
        )

    async def get_by_slug_public(self, slug: str, tenant_id: UUID) -> Category:
        stmt = (
            select(Category)
            .where(
                Category.tenant_id == tenant_id,
                Category.slug == slug,
                Category.is_active.is_(True),
                Category.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError("Category", slug)
        return category


# ============================================================================
# Product Service
# ============================================================================


class ProductService(BaseService[Product]):
    """Service for product CRUD, search, and relations."""

    model = Product

    def _get_default_options(self) -> list:
        return [selectinload(Product.images)]

    async def get_by_id(self, product_id: UUID, tenant_id: UUID) -> Product:
        return await self._get_by_id(product_id, tenant_id)

    async def get_with_includes(
        self,
        product_id: UUID,
        tenant_id: UUID,
        include: list[str] | None = None,
    ) -> Product:
        """Load product with optional eager-loaded relations."""
        options = [selectinload(Product.images)]
        if include:
            if "aliases" in include:
                options.append(selectinload(Product.aliases))
            if "categories" in include:
                options.append(
                    selectinload(Product.categories).selectinload(ProductCategory.category)
                )
            if "prices" in include:
                options.append(selectinload(Product.prices))
        return await self._get_by_id(product_id, tenant_id, options=options)

    async def list_products(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        brand: str | None = None,
        category_id: UUID | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Product], int]:
        filters = []
        if is_active is not None:
            filters.append(Product.is_active == is_active)
        if brand:
            filters.append(Product.brand.ilike(f"%{brand}%"))

        base_query = self._build_base_query(tenant_id, filters=filters)

        if search:
            pattern = f"%{search}%"
            base_query = base_query.where(
                or_(
                    Product.title.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.brand.ilike(pattern),
                    Product.model.ilike(pattern),
                )
            )

        if category_id:
            base_query = base_query.join(ProductCategory).where(
                ProductCategory.category_id == category_id
            )

        return await paginate_query(
            self.db, base_query, page, page_size,
            options=self._get_default_options(),
            order_by=[Product.created_at.desc()],
            unique=True,
        )

    @transactional
    async def create(self, tenant_id: UUID, data: ProductCreate) -> Product:
        stmt = select(Product).where(
            Product.tenant_id == tenant_id, Product.sku == data.sku,
            Product.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise AlreadyExistsError("Product", "sku", data.sku)

        slug_stmt = select(Product).where(
            Product.tenant_id == tenant_id, Product.slug == data.slug,
            Product.deleted_at.is_(None),
        )
        slug_result = await self.db.execute(slug_stmt)
        if slug_result.scalar_one_or_none():
            raise AlreadyExistsError("Product", "slug", data.slug)

        product = Product(
            tenant_id=tenant_id,
            sku=data.sku,
            slug=data.slug,
            title=data.title,
            brand=data.brand,
            model=data.model,
            description=data.description,
            uom_id=data.uom_id,
            is_active=data.is_active,
        )
        self.db.add(product)
        await self.db.flush()

        if data.category_ids:
            for i, cat_id in enumerate(data.category_ids):
                link = ProductCategory(
                    product_id=product.id,
                    category_id=cat_id,
                    is_primary=(i == 0),
                )
                self.db.add(link)

        await self.db.flush()
        await self.db.refresh(product)
        await self.db.refresh(product, ["images"])
        return product

    @transactional
    async def update(self, product_id: UUID, tenant_id: UUID, data: ProductUpdate) -> Product:
        product = await self.get_by_id(product_id, tenant_id)
        product.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})

        if "sku" in update_data and update_data["sku"] != product.sku:
            stmt = select(Product).where(
                Product.tenant_id == tenant_id,
                Product.sku == update_data["sku"],
                Product.id != product_id,
                Product.deleted_at.is_(None),
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                raise AlreadyExistsError("Product", "sku", update_data["sku"])

        if "slug" in update_data and update_data["slug"] != product.slug:
            slug_stmt = select(Product).where(
                Product.tenant_id == tenant_id,
                Product.slug == update_data["slug"],
                Product.id != product_id,
                Product.deleted_at.is_(None),
            )
            slug_result = await self.db.execute(slug_stmt)
            if slug_result.scalar_one_or_none():
                raise AlreadyExistsError("Product", "slug", update_data["slug"])

        for field, value in update_data.items():
            setattr(product, field, value)

        await self.db.flush()
        await self.db.refresh(product)
        await self.db.refresh(product, ["images"])
        return product

    @transactional
    async def soft_delete(self, product_id: UUID, tenant_id: UUID) -> None:
        await self._soft_delete(product_id, tenant_id)

    # ========== Public methods ==========

    async def list_published(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        brand: str | None = None,
        category_id: UUID | None = None,
    ) -> tuple[list[Product], int]:
        """List active products for public display."""
        filters = [
            Product.is_active.is_(True),
        ]
        if brand:
            filters.append(Product.brand.ilike(f"%{brand}%"))

        base_query = self._build_base_query(tenant_id, filters=filters)

        if search:
            pattern = f"%{search}%"
            base_query = base_query.where(
                or_(
                    Product.title.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.brand.ilike(pattern),
                )
            )

        if category_id:
            base_query = base_query.join(ProductCategory).where(
                ProductCategory.category_id == category_id
            )

        return await paginate_query(
            self.db, base_query, page, page_size,
            options=self._get_default_options(),
            order_by=[Product.created_at.desc()],
            unique=True,
        )

    async def get_by_slug_public(self, slug: str, tenant_id: UUID) -> Product:
        """Load a product by slug with all relations for the public detail page."""
        stmt = (
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.slug == slug,
                Product.is_active.is_(True),
                Product.deleted_at.is_(None),
            )
            .options(
                selectinload(Product.images),
                selectinload(Product.prices),
                selectinload(Product.categories).selectinload(ProductCategory.category),
            )
        )
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError("Product", slug)
        return product

    # ========== Aliases ==========

    async def list_aliases(self, product_id: UUID, tenant_id: UUID) -> list[ProductAlias]:
        await self.get_by_id(product_id, tenant_id)
        stmt = select(ProductAlias).where(ProductAlias.product_id == product_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def bulk_create_aliases(
        self, product_id: UUID, tenant_id: UUID, aliases: list[str],
    ) -> dict:
        await self.get_by_id(product_id, tenant_id)
        created = 0
        skipped = 0

        for alias_text in aliases:
            stmt = select(ProductAlias).where(
                ProductAlias.product_id == product_id,
                func.lower(ProductAlias.alias) == alias_text.lower(),
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                skipped += 1
            else:
                self.db.add(ProductAlias(product_id=product_id, alias=alias_text))
                created += 1

        await self.db.flush()
        return {"created": created, "skipped": skipped}

    @transactional
    async def delete_alias(self, product_id: UUID, alias_id: UUID, tenant_id: UUID) -> None:
        await self.get_by_id(product_id, tenant_id)
        stmt = select(ProductAlias).where(
            ProductAlias.id == alias_id, ProductAlias.product_id == product_id,
        )
        result = await self.db.execute(stmt)
        alias = result.scalar_one_or_none()
        if not alias:
            raise NotFoundError("ProductAlias", alias_id)
        await self.db.delete(alias)
        await self.db.flush()

    # ========== Analogs ==========

    async def list_analogs(self, product_id: UUID, tenant_id: UUID) -> list[dict]:
        await self.get_by_id(product_id, tenant_id)
        analog_product = aliased(Product)
        stmt = (
            select(ProductAnalog, analog_product)
            .join(analog_product, ProductAnalog.analog_product_id == analog_product.id)
            .where(ProductAnalog.product_id == product_id)
        )
        result = await self.db.execute(stmt)
        return [
            {
                "analog_product_id": row[1].id,
                "sku": row[1].sku,
                "title": row[1].title,
                "relation": row[0].relation,
                "notes": row[0].notes,
            }
            for row in result.all()
        ]

    @transactional
    async def add_analog(
        self, product_id: UUID, tenant_id: UUID, data: ProductAnalogCreate,
    ) -> ProductAnalog:
        await self.get_by_id(product_id, tenant_id)
        await self.get_by_id(data.analog_product_id, tenant_id)

        analog = ProductAnalog(
            product_id=product_id,
            analog_product_id=data.analog_product_id,
            relation=data.relation,
            notes=data.notes,
        )
        self.db.add(analog)
        await self.db.flush()
        return analog

    @transactional
    async def remove_analog(
        self, product_id: UUID, analog_product_id: UUID, tenant_id: UUID,
    ) -> None:
        await self.get_by_id(product_id, tenant_id)
        stmt = select(ProductAnalog).where(
            ProductAnalog.product_id == product_id,
            ProductAnalog.analog_product_id == analog_product_id,
        )
        result = await self.db.execute(stmt)
        analog = result.scalar_one_or_none()
        if not analog:
            raise NotFoundError("ProductAnalog", analog_product_id)
        await self.db.delete(analog)
        await self.db.flush()

    # ========== Prices ==========

    async def list_prices(self, product_id: UUID, tenant_id: UUID) -> list[ProductPrice]:
        await self.get_by_id(product_id, tenant_id)
        stmt = (
            select(ProductPrice)
            .where(ProductPrice.product_id == product_id)
            .order_by(ProductPrice.price_type, ProductPrice.valid_from.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def create_price(
        self, product_id: UUID, tenant_id: UUID, data: ProductPriceCreate,
    ) -> ProductPrice:
        await self.get_by_id(product_id, tenant_id)
        price = ProductPrice(product_id=product_id, **data.model_dump())
        self.db.add(price)
        await self.db.flush()
        await self.db.refresh(price)
        return price

    @transactional
    async def update_price(
        self, price_id: UUID, product_id: UUID, tenant_id: UUID, data: ProductPriceUpdate,
    ) -> ProductPrice:
        await self.get_by_id(product_id, tenant_id)
        stmt = select(ProductPrice).where(
            ProductPrice.id == price_id, ProductPrice.product_id == product_id,
        )
        result = await self.db.execute(stmt)
        price = result.scalar_one_or_none()
        if not price:
            raise NotFoundError("ProductPrice", price_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(price, field, value)

        await self.db.flush()
        await self.db.refresh(price)
        return price

    @transactional
    async def delete_price(self, price_id: UUID, product_id: UUID, tenant_id: UUID) -> None:
        await self.get_by_id(product_id, tenant_id)
        stmt = select(ProductPrice).where(
            ProductPrice.id == price_id, ProductPrice.product_id == product_id,
        )
        result = await self.db.execute(stmt)
        price = result.scalar_one_or_none()
        if not price:
            raise NotFoundError("ProductPrice", price_id)
        await self.db.delete(price)
        await self.db.flush()

    # ========== Categories ==========

    @transactional
    async def set_categories(
        self, product_id: UUID, tenant_id: UUID, category_ids: list[UUID],
    ) -> list[ProductCategory]:
        """Replace all category links for a product."""
        await self.get_by_id(product_id, tenant_id)

        # Remove existing links
        stmt = select(ProductCategory).where(ProductCategory.product_id == product_id)
        result = await self.db.execute(stmt)
        for link in result.scalars().all():
            await self.db.delete(link)
        await self.db.flush()

        # Create new links
        links = []
        for i, cat_id in enumerate(category_ids):
            link = ProductCategory(
                product_id=product_id, category_id=cat_id, is_primary=(i == 0),
            )
            self.db.add(link)
            links.append(link)

        await self.db.flush()
        return links


# ============================================================================
# Product Image Service
# ============================================================================


class ProductImageService:
    """Service for product image gallery management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_images(self, product_id: UUID, tenant_id: UUID) -> list[ProductImage]:
        # Verify product exists
        svc = ProductService(self.db)
        await svc.get_by_id(product_id, tenant_id)

        stmt = (
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def upload_image(
        self,
        product_id: UUID,
        tenant_id: UUID,
        file,
        alt: str | None = None,
        is_cover: bool = False,
    ) -> ProductImage:
        svc = ProductService(self.db)
        await svc.get_by_id(product_id, tenant_id)

        url = await image_upload_service.upload_image(
            file=file,
            tenant_id=tenant_id,
            folder="products",
            entity_id=product_id,
        )
        storage_key = image_upload_service._extract_s3_key_from_url(url) or ""

        if is_cover:
            stmt = (
                update(ProductImage)
                .where(ProductImage.product_id == product_id)
                .values(is_cover=False)
            )
            await self.db.execute(stmt)

        # Determine next sort_order
        max_stmt = select(func.max(ProductImage.sort_order)).where(
            ProductImage.product_id == product_id
        )
        max_order = (await self.db.execute(max_stmt)).scalar() or 0

        image = ProductImage(
            product_id=product_id,
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
    async def delete_image(self, product_id: UUID, image_id: UUID, tenant_id: UUID) -> None:
        svc = ProductService(self.db)
        await svc.get_by_id(product_id, tenant_id)

        stmt = select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id,
        )
        result = await self.db.execute(stmt)
        image = result.scalar_one_or_none()
        if not image:
            raise NotFoundError("ProductImage", image_id)

        await image_upload_service.delete_image(image.url)
        await self.db.delete(image)
        await self.db.flush()

    @transactional
    async def set_cover(self, product_id: UUID, image_id: UUID, tenant_id: UUID) -> None:
        svc = ProductService(self.db)
        await svc.get_by_id(product_id, tenant_id)

        # Unset all covers
        stmt = (
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_cover=False)
        )
        await self.db.execute(stmt)

        # Set new cover
        img_stmt = select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id,
        )
        result = await self.db.execute(img_stmt)
        image = result.scalar_one_or_none()
        if not image:
            raise NotFoundError("ProductImage", image_id)
        image.is_cover = True
        await self.db.flush()

    @transactional
    async def reorder_images(
        self, product_id: UUID, tenant_id: UUID, ordered_ids: list[UUID],
    ) -> None:
        svc = ProductService(self.db)
        await svc.get_by_id(product_id, tenant_id)

        for sort_order, img_id in enumerate(ordered_ids):
            stmt = (
                update(ProductImage)
                .where(
                    ProductImage.id == img_id,
                    ProductImage.product_id == product_id,
                )
                .values(sort_order=sort_order)
            )
            await self.db.execute(stmt)
        await self.db.flush()

    @transactional
    async def update_image(
        self, product_id: UUID, image_id: UUID, tenant_id: UUID,
        alt: str | None = None, sort_order: int | None = None,
    ) -> ProductImage:
        svc = ProductService(self.db)
        await svc.get_by_id(product_id, tenant_id)

        stmt = select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id,
        )
        result = await self.db.execute(stmt)
        image = result.scalar_one_or_none()
        if not image:
            raise NotFoundError("ProductImage", image_id)

        if alt is not None:
            image.alt = alt
        if sort_order is not None:
            image.sort_order = sort_order

        await self.db.flush()
        await self.db.refresh(image)
        return image
