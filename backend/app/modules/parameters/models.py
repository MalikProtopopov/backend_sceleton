"""Parameter and product characteristic models."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import (
    Base,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
)


# ============================================================================
# Parameter (attribute dictionary)
# ============================================================================


class Parameter(Base, UUIDMixin, TimestampMixin, TenantMixin):
    """Attribute dictionary entry with type and constraints."""

    __tablename__ = "parameters"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    value_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    uom_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="global",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_filterable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relations
    uom: Mapped["UOM | None"] = relationship(  # noqa: F821
        "UOM", lazy="joined",
    )
    values: Mapped[list["ParameterValue"]] = relationship(
        "ParameterValue",
        back_populates="parameter",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ParameterValue.sort_order",
    )

    __table_args__ = (
        Index("ix_parameters_tenant", "tenant_id"),
        Index("ix_parameters_active", "tenant_id", "is_active"),
        CheckConstraint(
            "value_type IN ('string', 'number', 'enum', 'bool', 'range')",
            name="ck_parameters_value_type",
        ),
        CheckConstraint(
            "scope IN ('global', 'category')",
            name="ck_parameters_scope",
        ),
    )

    def __repr__(self) -> str:
        return f"<Parameter {self.name} ({self.value_type})>"


# ============================================================================
# Parameter Values (for enum-type parameters)
# ============================================================================


class ParameterValue(Base, UUIDMixin, TimestampMixin):
    """Predefined value for an enum-type parameter."""

    __tablename__ = "parameter_values"

    parameter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parameters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parameter: Mapped["Parameter"] = relationship("Parameter", back_populates="values")

    __table_args__ = (
        UniqueConstraint("parameter_id", "label", name="uq_parameter_values_label"),
        Index("ix_parameter_values_parameter", "parameter_id"),
    )

    def __repr__(self) -> str:
        return f"<ParameterValue {self.label}>"


# ============================================================================
# Product Characteristic (normalized, via parameter dictionary)
# ============================================================================


class ProductCharacteristic(Base, UUIDMixin, TimestampMixin):
    """Typed product attribute value bound to a parameter definition."""

    __tablename__ = "product_characteristics"

    product_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parameters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parameter_value_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parameter_values.id", ondelete="SET NULL"),
        nullable=True,
    )
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    uom_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("uoms.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual",
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relations
    parameter: Mapped["Parameter"] = relationship("Parameter", lazy="joined")
    parameter_value: Mapped["ParameterValue | None"] = relationship(
        "ParameterValue", lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "product_id", "parameter_id",
            name="uq_product_characteristics_product_param",
        ),
        Index("ix_product_characteristics_product", "product_id"),
        Index("ix_product_characteristics_parameter", "parameter_id"),
        CheckConstraint(
            "source_type IN ('manual', 'import', 'system')",
            name="ck_product_characteristics_source",
        ),
    )

    def __repr__(self) -> str:
        return f"<ProductCharacteristic product={self.product_id} param={self.parameter_id}>"
