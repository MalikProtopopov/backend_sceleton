"""Unit tests for catalog services (Product, Category, UOM)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.catalog.models import Category, Product, ProductImage, UOM
from app.modules.catalog.schemas import CategoryCreate, CategoryUpdate, ProductCreate, ProductUpdate
from app.modules.catalog.service import CategoryService, ProductService, UOMService


# ============================================================================
# ProductService Tests
# ============================================================================


class TestProductService:
    """Tests for ProductService CRUD and public operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = Mock()
        db.delete = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def product_service(self, mock_db: AsyncMock) -> ProductService:
        return ProductService(mock_db)

    @pytest.fixture
    def tenant_id(self) -> "uuid4":
        return uuid4()

    @pytest.fixture
    def sample_product(self, tenant_id) -> Product:
        product = Product(
            id=uuid4(),
            tenant_id=tenant_id,
            sku="SKU-0001-AB",
            slug="test-product",
            title="Test Product",
            brand="TestBrand",
            model="Model-X1",
            description="A test product",
            is_active=True,
            version=1,
        )
        product.images = []
        product.aliases = []
        product.categories = []
        product.prices = []
        return product

    @pytest.fixture
    def inactive_product(self, tenant_id) -> Product:
        product = Product(
            id=uuid4(),
            tenant_id=tenant_id,
            sku="SKU-0002-CD",
            slug="inactive-product",
            title="Inactive Product",
            is_active=False,
            version=1,
        )
        product.images = []
        return product

    # ========== get_by_id ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, product_service: ProductService, mock_db: AsyncMock, sample_product: Product,
    ) -> None:
        """Get by ID should return product when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value = mock_result

        product = await product_service.get_by_id(sample_product.id, sample_product.tenant_id)

        assert product.id == sample_product.id
        assert product.sku == "SKU-0001-AB"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, product_service: ProductService, mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when product doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await product_service.get_by_id(uuid4(), uuid4())

    # ========== create ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_product_success(
        self, product_service: ProductService, mock_db: AsyncMock, tenant_id,
    ) -> None:
        """Create should add a new product with slug."""
        sku_check = Mock()
        sku_check.scalar_one_or_none.return_value = None
        slug_check = Mock()
        slug_check.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [sku_check, slug_check]

        data = ProductCreate(
            sku="NEW-SKU-001",
            slug="new-product",
            title="New Product",
            brand="Brand",
        )

        await product_service.create(tenant_id, data)

        mock_db.add.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_product_duplicate_sku(
        self, product_service: ProductService, mock_db: AsyncMock,
        tenant_id, sample_product: Product,
    ) -> None:
        """Create should raise AlreadyExistsError when SKU is taken."""
        sku_check = Mock()
        sku_check.scalar_one_or_none.return_value = sample_product

        mock_db.execute.side_effect = [sku_check]

        data = ProductCreate(
            sku=sample_product.sku,
            slug="different-slug",
            title="Another Product",
        )

        with pytest.raises(AlreadyExistsError):
            await product_service.create(tenant_id, data)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_product_duplicate_slug(
        self, product_service: ProductService, mock_db: AsyncMock,
        tenant_id, sample_product: Product,
    ) -> None:
        """Create should raise AlreadyExistsError when slug is taken."""
        sku_check = Mock()
        sku_check.scalar_one_or_none.return_value = None
        slug_check = Mock()
        slug_check.scalar_one_or_none.return_value = sample_product

        mock_db.execute.side_effect = [sku_check, slug_check]

        data = ProductCreate(
            sku="UNIQUE-SKU",
            slug=sample_product.slug,
            title="Another Product",
        )

        with pytest.raises(AlreadyExistsError):
            await product_service.create(tenant_id, data)

    # ========== update ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_product_success(
        self, product_service: ProductService, mock_db: AsyncMock, sample_product: Product,
    ) -> None:
        """Update should modify product fields."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value = mock_result

        data = ProductUpdate(title="Updated Title", version=1)
        product = await product_service.update(
            sample_product.id, sample_product.tenant_id, data,
        )

        assert product.title == "Updated Title"

    # ========== soft_delete ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self, product_service: ProductService, mock_db: AsyncMock, sample_product: Product,
    ) -> None:
        """Soft delete should set deleted_at."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value = mock_result

        assert sample_product.deleted_at is None

        await product_service.soft_delete(sample_product.id, sample_product.tenant_id)

        assert sample_product.deleted_at is not None
        mock_db.flush.assert_called()

    # ========== list_published ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_returns_active_only(
        self, product_service: ProductService, mock_db: AsyncMock,
        sample_product: Product, tenant_id,
    ) -> None:
        """list_published should only return active products."""
        count_result = Mock()
        count_result.scalar.return_value = 1

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = [sample_product]

        mock_db.execute.side_effect = [count_result, list_result]

        products, total = await product_service.list_published(tenant_id)

        assert total == 1
        assert len(products) == 1
        assert products[0].is_active is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_published_empty(
        self, product_service: ProductService, mock_db: AsyncMock, tenant_id,
    ) -> None:
        """list_published should return empty when no active products."""
        count_result = Mock()
        count_result.scalar.return_value = 0

        list_result = Mock()
        list_result.scalars.return_value.unique.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_result, list_result]

        products, total = await product_service.list_published(tenant_id)

        assert products == []
        assert total == 0

    # ========== get_by_slug_public ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_public_success(
        self, product_service: ProductService, mock_db: AsyncMock, sample_product: Product,
    ) -> None:
        """get_by_slug_public should return active product by slug."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value = mock_result

        product = await product_service.get_by_slug_public(
            "test-product", sample_product.tenant_id,
        )

        assert product.slug == "test-product"
        assert product.is_active is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_public_not_found(
        self, product_service: ProductService, mock_db: AsyncMock,
    ) -> None:
        """get_by_slug_public should raise NotFoundError when slug not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await product_service.get_by_slug_public("nonexistent", uuid4())


# ============================================================================
# CategoryService Tests
# ============================================================================


class TestCategoryService:
    """Tests for CategoryService CRUD and public operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = Mock()
        db.delete = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def category_service(self, mock_db: AsyncMock) -> CategoryService:
        return CategoryService(mock_db)

    @pytest.fixture
    def tenant_id(self) -> "uuid4":
        return uuid4()

    @pytest.fixture
    def sample_category(self, tenant_id) -> Category:
        return Category(
            id=uuid4(),
            tenant_id=tenant_id,
            title="Electronics",
            slug="electronics",
            parent_id=None,
            description="Electronic products",
            is_active=True,
            sort_order=0,
            version=1,
        )

    # ========== get_by_id ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, category_service: CategoryService, mock_db: AsyncMock,
        sample_category: Category,
    ) -> None:
        """Get by ID should return category when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_category
        mock_db.execute.return_value = mock_result

        category = await category_service.get_by_id(
            sample_category.id, sample_category.tenant_id,
        )

        assert category.id == sample_category.id
        assert category.title == "Electronics"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, category_service: CategoryService, mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await category_service.get_by_id(uuid4(), uuid4())

    # ========== create ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_category_success(
        self, category_service: CategoryService, mock_db: AsyncMock, tenant_id,
    ) -> None:
        """Create should add a new category."""
        slug_check = Mock()
        slug_check.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = slug_check

        data = CategoryCreate(title="New Category", slug="new-category")

        await category_service.create(tenant_id, data)

        mock_db.add.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_category_duplicate_slug(
        self, category_service: CategoryService, mock_db: AsyncMock,
        tenant_id, sample_category: Category,
    ) -> None:
        """Create should raise AlreadyExistsError when slug is taken."""
        slug_check = Mock()
        slug_check.scalar_one_or_none.return_value = sample_category
        mock_db.execute.return_value = slug_check

        data = CategoryCreate(title="Another", slug=sample_category.slug)

        with pytest.raises(AlreadyExistsError):
            await category_service.create(tenant_id, data)

    # ========== update ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_category_success(
        self, category_service: CategoryService, mock_db: AsyncMock,
        sample_category: Category,
    ) -> None:
        """Update should modify category fields."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_category
        mock_db.execute.return_value = mock_result

        data = CategoryUpdate(title="Updated Electronics", version=1)
        category = await category_service.update(
            sample_category.id, sample_category.tenant_id, data,
        )

        assert category.title == "Updated Electronics"

    # ========== soft_delete ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_soft_delete_success(
        self, category_service: CategoryService, mock_db: AsyncMock,
        sample_category: Category,
    ) -> None:
        """Soft delete should set deleted_at."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_category
        mock_db.execute.return_value = mock_result

        assert sample_category.deleted_at is None

        await category_service.soft_delete(sample_category.id, sample_category.tenant_id)

        assert sample_category.deleted_at is not None
        mock_db.flush.assert_called()

    # ========== list_public ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_public_returns_active_categories(
        self, category_service: CategoryService, mock_db: AsyncMock,
        sample_category: Category, tenant_id,
    ) -> None:
        """list_public should return only active categories."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_category]
        mock_db.execute.return_value = mock_result

        categories = await category_service.list_public(tenant_id)

        assert len(categories) == 1
        assert categories[0].is_active is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_public_empty(
        self, category_service: CategoryService, mock_db: AsyncMock, tenant_id,
    ) -> None:
        """list_public should return empty list when no active categories."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        categories = await category_service.list_public(tenant_id)

        assert categories == []

    # ========== get_by_slug_public ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_public_success(
        self, category_service: CategoryService, mock_db: AsyncMock,
        sample_category: Category,
    ) -> None:
        """get_by_slug_public should return active category by slug."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_category
        mock_db.execute.return_value = mock_result

        category = await category_service.get_by_slug_public(
            "electronics", sample_category.tenant_id,
        )

        assert category.slug == "electronics"
        assert category.is_active is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_slug_public_not_found(
        self, category_service: CategoryService, mock_db: AsyncMock,
    ) -> None:
        """get_by_slug_public should raise NotFoundError when slug not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await category_service.get_by_slug_public("nonexistent", uuid4())


# ============================================================================
# UOMService Tests
# ============================================================================


class TestUOMService:
    """Tests for UOMService basic operations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        db.add = Mock()
        db.delete = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def uom_service(self, mock_db: AsyncMock) -> UOMService:
        return UOMService(mock_db)

    @pytest.fixture
    def tenant_id(self) -> "uuid4":
        return uuid4()

    @pytest.fixture
    def sample_uom(self, tenant_id) -> UOM:
        return UOM(
            id=uuid4(),
            tenant_id=tenant_id,
            name="Kilogram",
            code="KG",
            symbol="kg",
            is_active=True,
        )

    # ========== get_by_id ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, uom_service: UOMService, mock_db: AsyncMock, sample_uom: UOM,
    ) -> None:
        """Get by ID should return UOM when found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_uom
        mock_db.execute.return_value = mock_result

        uom = await uom_service.get_by_id(sample_uom.id, sample_uom.tenant_id)

        assert uom.id == sample_uom.id
        assert uom.code == "KG"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, uom_service: UOMService, mock_db: AsyncMock,
    ) -> None:
        """Get by ID should raise NotFoundError when UOM doesn't exist."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(NotFoundError):
            await uom_service.get_by_id(uuid4(), uuid4())

    # ========== list_all ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_all_active(
        self, uom_service: UOMService, mock_db: AsyncMock, sample_uom: UOM, tenant_id,
    ) -> None:
        """list_all should return active UOMs."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_uom]
        mock_db.execute.return_value = mock_result

        uoms = await uom_service.list_all(tenant_id)

        assert len(uoms) == 1
        assert uoms[0].is_active is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_all_empty(
        self, uom_service: UOMService, mock_db: AsyncMock, tenant_id,
    ) -> None:
        """list_all should return empty list when no UOMs exist."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        uoms = await uom_service.list_all(tenant_id)

        assert uoms == []

    # ========== create ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_uom_success(
        self, uom_service: UOMService, mock_db: AsyncMock, tenant_id,
    ) -> None:
        """Create should add a new UOM."""
        code_check = Mock()
        code_check.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = code_check

        await uom_service.create(tenant_id, name="Piece", code="PCS", symbol="pcs")

        mock_db.add.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_uom_duplicate_code(
        self, uom_service: UOMService, mock_db: AsyncMock,
        tenant_id, sample_uom: UOM,
    ) -> None:
        """Create should raise AlreadyExistsError when code is taken."""
        code_check = Mock()
        code_check.scalar_one_or_none.return_value = sample_uom
        mock_db.execute.return_value = code_check

        with pytest.raises(AlreadyExistsError):
            await uom_service.create(tenant_id, name="Kilogram", code="KG")

    # ========== update ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_uom_success(
        self, uom_service: UOMService, mock_db: AsyncMock, sample_uom: UOM,
    ) -> None:
        """Update should modify UOM fields."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_uom
        mock_db.execute.return_value = mock_result

        uom = await uom_service.update(
            sample_uom.id, sample_uom.tenant_id, name="Updated Kilogram",
        )

        assert uom.name == "Updated Kilogram"

    # ========== deactivate ==========

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deactivate_uom(
        self, uom_service: UOMService, mock_db: AsyncMock, sample_uom: UOM,
    ) -> None:
        """Deactivate should set is_active to False."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_uom
        mock_db.execute.return_value = mock_result

        assert sample_uom.is_active is True

        await uom_service.deactivate(sample_uom.id, sample_uom.tenant_id)

        assert sample_uom.is_active is False
        mock_db.flush.assert_called()
