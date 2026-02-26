"""Product catalog database models."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import (
    Base,
    SoftDeleteMixin,
    SortOrderMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


# ============================================================================
# Unit of Measure
# ============================================================================


class UOM(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Unit of measure (kg, m, pcs, etc.)."""

    __tablename__ = "uoms"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_uoms_tenant_code"),
        Index("ix_uoms_tenant", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<UOM {self.code}>"


# ============================================================================
# Categories (hierarchical)
# ============================================================================


class Category(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Hierarchical product category."""

    __tablename__ = "categories"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        lazy="noload",
    )
    parent: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="children",
        remote_side="Category.id",
        lazy="noload",
    )
    products: Mapped[list["ProductCategory"]] = relationship(
        "ProductCategory",
        back_populates="category",
        lazy="noload",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_categories_tenant_slug"),
        Index("ix_categories_tenant", "tenant_id"),
        Index(
            "ix_categories_active",
            "tenant_id",
            "is_active",
            postgresql_where="deleted_at IS NULL AND is_active = true",
        ),
    )

    def __repr__(self) -> str:
        return f"<Category {self.slug}>"


# ============================================================================
# Products
# ============================================================================


class Product(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin
):
    """Core product entity."""

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uom_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relations
    uom: Mapped["UOM | None"] = relationship("UOM", lazy="joined")
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )
    aliases: Mapped[list["ProductAlias"]] = relationship(
        "ProductAlias",
        back_populates="product",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    categories: Mapped[list["ProductCategory"]] = relationship(
        "ProductCategory",
        back_populates="product",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    prices: Mapped[list["ProductPrice"]] = relationship(
        "ProductPrice",
        back_populates="product",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
        UniqueConstraint("tenant_id", "slug", name="uq_products_tenant_slug"),
        Index("ix_products_tenant", "tenant_id"),
        Index("ix_products_title", "title"),
        Index(
            "ix_products_active",
            "tenant_id",
            "is_active",
            postgresql_where="deleted_at IS NULL AND is_active = true",
        ),
    )

    def __repr__(self) -> str:
        return f"<Product {self.sku}>"


# ============================================================================
# Product Images (gallery)
# ============================================================================


class ProductImage(Base, UUIDMixin):
    """Product image in a gallery."""

    __tablename__ = "product_images"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    alt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_cover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    product: Mapped["Product"] = relationship("Product", back_populates="images")

    __table_args__ = (
        Index("ix_product_images_product", "product_id"),
        Index("ix_product_images_cover", "product_id", "is_cover"),
    )

    def __repr__(self) -> str:
        return f"<ProductImage {self.id} order={self.sort_order}>"


# ============================================================================
# Product Aliases (search helpers)
# ============================================================================


class ProductAlias(Base, UUIDMixin):
    """Alternative name for product search and matching."""

    __tablename__ = "product_aliases"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False, index=True)

    product: Mapped["Product"] = relationship("Product", back_populates="aliases")

    __table_args__ = (
        Index("ix_product_aliases_product", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<ProductAlias {self.alias}>"


# ============================================================================
# Product Analogs (directed relationship)
# ============================================================================


class ProductAnalog(Base):
    """Directed analog/substitute relationship between products."""

    __tablename__ = "product_analogs"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    analog_product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relation: Mapped[str] = mapped_column(
        String(20), nullable=False, default="equivalent",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "relation IN ('equivalent', 'better', 'worse')",
            name="ck_product_analogs_relation",
        ),
        CheckConstraint(
            "product_id != analog_product_id",
            name="ck_product_analogs_no_self_ref",
        ),
    )

    def __repr__(self) -> str:
        return f"<ProductAnalog {self.product_id}->{self.analog_product_id}>"


# ============================================================================
# Product-Category (many-to-many with primary flag)
# ============================================================================


class ProductCategory(Base, UUIDMixin):
    """Link between product and category with primary flag."""

    __tablename__ = "product_categories"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product: Mapped["Product"] = relationship("Product", back_populates="categories")
    category: Mapped["Category"] = relationship("Category", back_populates="products")

    __table_args__ = (
        UniqueConstraint("product_id", "category_id", name="uq_product_categories"),
        Index("ix_product_categories_product", "product_id"),
        Index("ix_product_categories_category", "category_id"),
    )

    def __repr__(self) -> str:
        return f"<ProductCategory product={self.product_id} cat={self.category_id}>"


# ============================================================================
# Product Prices (temporal, multi-type)
# ============================================================================


class ProductPrice(Base, UUIDMixin, TimestampMixin):
    """Product price with type and validity period."""

    __tablename__ = "product_prices"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="regular",
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    valid_from: Mapped[datetime | None] = mapped_column(Date, nullable=True, index=True)
    valid_to: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    product: Mapped["Product"] = relationship("Product", back_populates="prices")

    __table_args__ = (
        CheckConstraint(
            "price_type IN ('regular', 'sale', 'wholesale', 'cost')",
            name="ck_product_prices_type",
        ),
        CheckConstraint("amount >= 0", name="ck_product_prices_amount_positive"),
        Index("ix_product_prices_product", "product_id"),
        Index("ix_product_prices_valid", "product_id", "price_type", "valid_from"),
    )

    def __repr__(self) -> str:
        return f"<ProductPrice {self.price_type} {self.amount}>"
