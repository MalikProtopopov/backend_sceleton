"""Product variant and option group models."""

from datetime import date, datetime
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
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


# ============================================================================
# Option Groups (axes of variation)
# ============================================================================


class ProductOptionGroup(Base, UUIDMixin, TimestampMixin):
    """Axis of variation for a product (e.g. Color, Size, Tariff Plan)."""

    __tablename__ = "product_option_groups"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    tenant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    display_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="dropdown",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    parameter_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parameters.id", ondelete="SET NULL"),
        nullable=True,
    )

    product = relationship("Product", back_populates="option_groups")
    values: Mapped[list["ProductOptionValue"]] = relationship(
        "ProductOptionValue",
        back_populates="option_group",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ProductOptionValue.sort_order",
    )

    __table_args__ = (
        UniqueConstraint("product_id", "slug", name="uq_option_groups_product_slug"),
        CheckConstraint(
            "display_type IN ('dropdown', 'buttons', 'color_swatch', 'cards')",
            name="ck_option_groups_display_type",
        ),
        Index("ix_option_groups_product", "product_id"),
    )

    def __repr__(self) -> str:
        return f"<ProductOptionGroup {self.slug}>"


# ============================================================================
# Option Values
# ============================================================================


class ProductOptionValue(Base, UUIDMixin, TimestampMixin):
    """A specific choice within an option group (e.g. Red, XL, Premium)."""

    __tablename__ = "product_option_values"

    option_group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_option_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    option_group: Mapped["ProductOptionGroup"] = relationship(
        "ProductOptionGroup", back_populates="values", lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "option_group_id", "slug",
            name="uq_option_values_group_slug",
        ),
        Index("ix_option_values_group", "option_group_id"),
    )

    def __repr__(self) -> str:
        return f"<ProductOptionValue {self.slug}>"


# ============================================================================
# Product Variant (Offer / торговое предложение)
# ============================================================================


class ProductVariant(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin):
    """A purchasable variant of a product with its own SKU, price, and stock."""

    __tablename__ = "product_variants"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    stock_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)

    product = relationship("Product", back_populates="variants")
    prices: Mapped[list["VariantPrice"]] = relationship(
        "VariantPrice",
        back_populates="variant",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    option_links: Mapped[list["VariantOptionLink"]] = relationship(
        "VariantOptionLink",
        back_populates="variant",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    images: Mapped[list["VariantImage"]] = relationship(
        "VariantImage",
        back_populates="variant",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="VariantImage.sort_order",
    )
    inclusions: Mapped[list["VariantInclusion"]] = relationship(
        "VariantInclusion",
        back_populates="variant",
        lazy="noload",
        cascade="all, delete-orphan",
        order_by="VariantInclusion.sort_order",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "sku", name="uq_variants_tenant_sku"),
        UniqueConstraint("product_id", "slug", name="uq_variants_product_slug"),
        Index(
            "ix_variants_product_active",
            "product_id",
            postgresql_where="deleted_at IS NULL",
        ),
        Index("ix_variants_tenant_active", "tenant_id", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<ProductVariant {self.sku}>"


# ============================================================================
# Variant Price (temporal, multi-type — same pattern as ProductPrice)
# ============================================================================


class VariantPrice(Base, UUIDMixin, TimestampMixin):
    """Variant price with type and validity period."""

    __tablename__ = "variant_prices"

    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    price_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="regular",
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="prices",
    )

    __table_args__ = (
        CheckConstraint(
            "price_type IN ('regular', 'sale', 'wholesale', 'cost')",
            name="ck_variant_prices_type",
        ),
        CheckConstraint("amount >= 0", name="ck_variant_prices_amount_positive"),
        Index("ix_variant_prices_valid", "variant_id", "price_type", "valid_from"),
    )

    def __repr__(self) -> str:
        return f"<VariantPrice {self.price_type} {self.amount}>"


# ============================================================================
# Variant ↔ Option Value link (M2M)
# ============================================================================


class VariantOptionLink(Base, UUIDMixin):
    """Links a variant to the option values that define it."""

    __tablename__ = "variant_option_links"

    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    option_value_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_option_values.id", ondelete="CASCADE"),
        nullable=False,
    )

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="option_links",
    )
    option_value: Mapped["ProductOptionValue"] = relationship(
        "ProductOptionValue", lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "variant_id", "option_value_id",
            name="uq_variant_option_links",
        ),
        Index("ix_variant_option_links_variant", "variant_id"),
        Index("ix_variant_option_links_value", "option_value_id"),
    )

    def __repr__(self) -> str:
        return f"<VariantOptionLink variant={self.variant_id} value={self.option_value_id}>"


# ============================================================================
# Variant Inclusion (tariff feature list for comparison tables)
# ============================================================================


class VariantInclusion(Base, UUIDMixin, TimestampMixin):
    """A feature/benefit included (or not) in a variant, for tariff comparison."""

    __tablename__ = "variant_inclusions"

    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group: Mapped[str | None] = mapped_column(String(100), nullable=True)

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="inclusions",
    )

    __table_args__ = (
        Index("ix_variant_inclusions_variant", "variant_id"),
    )

    def __repr__(self) -> str:
        return f"<VariantInclusion {self.title[:30]}>"


# ============================================================================
# Variant Image (variant-specific gallery)
# ============================================================================


class VariantImage(Base, UUIDMixin):
    """Image specific to a product variant."""

    __tablename__ = "variant_images"

    variant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
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

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="images",
    )

    __table_args__ = (
        Index("ix_variant_images_cover", "variant_id", "is_cover"),
    )

    def __repr__(self) -> str:
        return f"<VariantImage {self.id} order={self.sort_order}>"
