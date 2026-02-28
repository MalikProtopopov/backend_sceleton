"""Parameter and product characteristic service layer."""

from uuid import UUID

from slugify import slugify
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.base_service import BaseService
from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError, ValidationError
from app.core.pagination import paginate_query
from app.modules.catalog.models import Product
from app.modules.parameters.models import (
    Parameter,
    ParameterCategory,
    ParameterValue,
    ProductCharacteristic,
)
from app.modules.parameters.schemas import (
    ParameterCreate,
    ParameterUpdate,
    ParameterValueCreate,
    ProductCharacteristicBulkItem,
    ProductCharacteristicCreate,
)


def _generate_slug(text: str) -> str:
    return slugify(text, lowercase=True, max_length=255)


async def _ensure_unique_slug(
    db: AsyncSession,
    table,
    slug: str,
    scope_filters: list,
    exclude_id: UUID | None = None,
    max_attempts: int = 100,
) -> str:
    """Append numeric suffix if slug already exists within scope."""
    candidate = slug
    counter = 0
    while counter <= max_attempts:
        filters = [*scope_filters, table.slug == candidate]
        if exclude_id:
            filters.append(table.id != exclude_id)
        stmt = select(func.count()).where(*filters)
        count = (await db.execute(stmt)).scalar() or 0
        if count == 0:
            return candidate
        counter += 1
        candidate = f"{slug}-{counter}"
    return f"{slug}-{counter}"


# ============================================================================
# Parameter Service
# ============================================================================


class ParameterService(BaseService[Parameter]):
    """Service for attribute dictionary management."""

    model = Parameter

    def _get_default_options(self) -> list:
        return [selectinload(Parameter.values), selectinload(Parameter.category_links)]

    async def get_by_id(self, parameter_id: UUID, tenant_id: UUID) -> Parameter:
        return await self._get_by_id(parameter_id, tenant_id)

    async def list_parameters(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        value_type: str | None = None,
        scope: str | None = None,
        active_only: bool = True,
    ) -> tuple[list[Parameter], int]:
        filters = []
        if active_only:
            filters.append(Parameter.is_active.is_(True))
        if value_type:
            filters.append(Parameter.value_type == value_type)
        if scope:
            filters.append(Parameter.scope == scope)

        base_query = self._build_base_query(tenant_id, filters=filters)

        if search:
            base_query = base_query.where(Parameter.name.ilike(f"%{search}%"))

        return await paginate_query(
            self.db, base_query, page, page_size,
            options=self._get_default_options(),
            order_by=[Parameter.sort_order, Parameter.name],
        )

    def _build_parameter_response_data(self, param: Parameter) -> dict:
        """Extract category_ids from loaded category_links."""
        category_ids = [link.category_id for link in (param.category_links or [])]
        return {"category_ids": category_ids}

    @transactional
    async def create(self, tenant_id: UUID, data: ParameterCreate) -> Parameter:
        slug = data.slug or _generate_slug(data.name)
        slug = await _ensure_unique_slug(
            self.db, Parameter, slug,
            [Parameter.tenant_id == tenant_id],
        )

        param = Parameter(
            tenant_id=tenant_id,
            name=data.name,
            slug=slug,
            value_type=data.value_type,
            uom_id=data.uom_id,
            scope=data.scope,
            description=data.description,
            constraints=data.constraints,
            is_filterable=data.is_filterable,
            is_required=data.is_required,
            sort_order=data.sort_order,
        )
        self.db.add(param)
        await self.db.flush()

        if data.values:
            for i, val_data in enumerate(data.values):
                val_slug = val_data.slug or _generate_slug(val_data.label)
                val_slug = await _ensure_unique_slug(
                    self.db, ParameterValue, val_slug,
                    [ParameterValue.parameter_id == param.id],
                )
                pv = ParameterValue(
                    parameter_id=param.id,
                    label=val_data.label,
                    slug=val_slug,
                    code=val_data.code,
                    sort_order=val_data.sort_order if val_data.sort_order is not None else i,
                )
                self.db.add(pv)

        if data.category_ids:
            for cat_id in data.category_ids:
                self.db.add(ParameterCategory(parameter_id=param.id, category_id=cat_id))

        await self.db.flush()
        await self.db.refresh(param)
        await self.db.refresh(param, ["values", "category_links"])
        return param

    @transactional
    async def update(self, parameter_id: UUID, tenant_id: UUID, data: ParameterUpdate) -> Parameter:
        param = await self.get_by_id(parameter_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        if "slug" in update_data and update_data["slug"]:
            new_slug = await _ensure_unique_slug(
                self.db, Parameter, update_data["slug"],
                [Parameter.tenant_id == tenant_id],
                exclude_id=parameter_id,
            )
            update_data["slug"] = new_slug
        elif "name" in update_data and "slug" not in update_data:
            new_slug = _generate_slug(update_data["name"])
            new_slug = await _ensure_unique_slug(
                self.db, Parameter, new_slug,
                [Parameter.tenant_id == tenant_id],
                exclude_id=parameter_id,
            )
            update_data["slug"] = new_slug

        for field, value in update_data.items():
            if hasattr(param, field):
                setattr(param, field, value)

        await self.db.flush()
        await self.db.refresh(param)
        await self.db.refresh(param, ["values", "category_links"])
        return param

    @transactional
    async def deactivate(self, parameter_id: UUID, tenant_id: UUID) -> None:
        """Soft-archive a parameter (is_active=False instead of delete)."""
        param = await self.get_by_id(parameter_id, tenant_id)
        param.is_active = False
        await self.db.flush()

    @transactional
    async def set_categories(
        self, parameter_id: UUID, tenant_id: UUID, category_ids: list[UUID],
    ) -> list[UUID]:
        """Replace all category links for a parameter."""
        await self.get_by_id(parameter_id, tenant_id)
        await self.db.execute(
            delete(ParameterCategory).where(ParameterCategory.parameter_id == parameter_id)
        )
        await self.db.flush()
        for cat_id in set(category_ids):
            self.db.add(ParameterCategory(parameter_id=parameter_id, category_id=cat_id))
        await self.db.flush()
        return list(set(category_ids))

    # ========== Parameter Values ==========

    @transactional
    async def create_value(
        self, parameter_id: UUID, tenant_id: UUID, data: ParameterValueCreate,
    ) -> ParameterValue:
        param = await self.get_by_id(parameter_id, tenant_id)
        if param.value_type != "enum":
            raise ValidationError(
                f"Cannot add predefined values to a '{param.value_type}' parameter"
            )

        stmt = select(ParameterValue).where(
            ParameterValue.parameter_id == parameter_id,
            ParameterValue.label == data.label,
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise AlreadyExistsError("ParameterValue", "label", data.label)

        val_slug = data.slug or _generate_slug(data.label)
        val_slug = await _ensure_unique_slug(
            self.db, ParameterValue, val_slug,
            [ParameterValue.parameter_id == parameter_id],
        )

        max_stmt = select(func.max(ParameterValue.sort_order)).where(
            ParameterValue.parameter_id == parameter_id
        )
        max_order = (await self.db.execute(max_stmt)).scalar() or 0

        pv = ParameterValue(
            parameter_id=parameter_id,
            label=data.label,
            slug=val_slug,
            code=data.code,
            sort_order=data.sort_order if data.sort_order is not None else max_order + 1,
        )
        self.db.add(pv)
        await self.db.flush()
        await self.db.refresh(pv)
        return pv

    @transactional
    async def update_value(
        self, value_id: UUID, parameter_id: UUID, tenant_id: UUID,
        label: str | None = None, slug: str | None = None,
        code: str | None = None, sort_order: int | None = None,
        is_active: bool | None = None,
    ) -> ParameterValue:
        await self.get_by_id(parameter_id, tenant_id)
        stmt = select(ParameterValue).where(
            ParameterValue.id == value_id,
            ParameterValue.parameter_id == parameter_id,
        )
        result = await self.db.execute(stmt)
        pv = result.scalar_one_or_none()
        if not pv:
            raise NotFoundError("ParameterValue", value_id)

        if label is not None:
            pv.label = label
            if slug is None:
                new_slug = _generate_slug(label)
                pv.slug = await _ensure_unique_slug(
                    self.db, ParameterValue, new_slug,
                    [ParameterValue.parameter_id == parameter_id],
                    exclude_id=value_id,
                )
        if slug is not None:
            pv.slug = await _ensure_unique_slug(
                self.db, ParameterValue, slug,
                [ParameterValue.parameter_id == parameter_id],
                exclude_id=value_id,
            )
        if code is not None:
            pv.code = code
        if sort_order is not None:
            pv.sort_order = sort_order
        if is_active is not None:
            pv.is_active = is_active

        await self.db.flush()
        await self.db.refresh(pv)
        return pv

    @transactional
    async def delete_value(self, value_id: UUID, parameter_id: UUID, tenant_id: UUID) -> None:
        await self.get_by_id(parameter_id, tenant_id)
        stmt = select(ParameterValue).where(
            ParameterValue.id == value_id,
            ParameterValue.parameter_id == parameter_id,
        )
        result = await self.db.execute(stmt)
        pv = result.scalar_one_or_none()
        if not pv:
            raise NotFoundError("ParameterValue", value_id)
        await self.db.delete(pv)
        await self.db.flush()


# ============================================================================
# Product Characteristic Service
# ============================================================================


class ProductCharacteristicService:
    """Service for normalized product characteristics (via parameter dict)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _verify_product(self, product_id: UUID, tenant_id: UUID) -> None:
        stmt = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id,
            Product.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        if not result.scalar_one_or_none():
            raise NotFoundError("Product", product_id)

    async def list_for_product(self, product_id: UUID, tenant_id: UUID) -> list[ProductCharacteristic]:
        await self._verify_product(product_id, tenant_id)
        stmt = (
            select(ProductCharacteristic)
            .where(ProductCharacteristic.product_id == product_id)
            .order_by(ProductCharacteristic.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def set_characteristic(
        self, product_id: UUID, tenant_id: UUID, data: ProductCharacteristicCreate,
    ) -> ProductCharacteristic:
        """Create or update a product characteristic. Auto-creates enum values."""
        await self._verify_product(product_id, tenant_id)

        stmt = select(Parameter).where(
            Parameter.id == data.parameter_id,
            Parameter.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        param = result.scalar_one_or_none()
        if not param:
            raise NotFoundError("Parameter", data.parameter_id)

        parameter_value_id = data.parameter_value_id
        if param.value_type == "enum" and data.value_text and not parameter_value_id:
            parameter_value_id = await self._ensure_enum_value(param.id, data.value_text)

        if param.value_type == "enum" and parameter_value_id:
            stmt = select(ProductCharacteristic).where(
                ProductCharacteristic.product_id == product_id,
                ProductCharacteristic.parameter_id == data.parameter_id,
                ProductCharacteristic.parameter_value_id == parameter_value_id,
            )
        else:
            stmt = select(ProductCharacteristic).where(
                ProductCharacteristic.product_id == product_id,
                ProductCharacteristic.parameter_id == data.parameter_id,
                ProductCharacteristic.parameter_value_id.is_(None),
            )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            if existing.is_locked:
                raise ValidationError("This characteristic is locked and cannot be modified")
            existing.parameter_value_id = parameter_value_id
            existing.value_text = data.value_text
            existing.value_number = data.value_number
            existing.value_bool = data.value_bool
            existing.uom_id = data.uom_id
            existing.source_type = data.source_type or "manual"
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        char = ProductCharacteristic(
            product_id=product_id,
            parameter_id=data.parameter_id,
            parameter_value_id=parameter_value_id,
            value_text=data.value_text,
            value_number=data.value_number,
            value_bool=data.value_bool,
            uom_id=data.uom_id,
            source_type=data.source_type or "manual",
        )
        self.db.add(char)
        await self.db.flush()
        await self.db.refresh(char)
        return char

    @transactional
    async def bulk_set(
        self,
        product_id: UUID,
        tenant_id: UUID,
        items: list[ProductCharacteristicBulkItem],
    ) -> dict:
        """Bulk set characteristics for a product. Replaces per-parameter."""
        await self._verify_product(product_id, tenant_id)
        created = 0
        updated = 0
        deleted = 0

        for item in items:
            stmt = select(Parameter).where(
                Parameter.id == item.parameter_id,
                Parameter.tenant_id == tenant_id,
            )
            result = await self.db.execute(stmt)
            param = result.scalar_one_or_none()
            if not param:
                raise NotFoundError("Parameter", item.parameter_id)

            # Delete existing characteristics for this parameter
            del_stmt = select(ProductCharacteristic).where(
                ProductCharacteristic.product_id == product_id,
                ProductCharacteristic.parameter_id == item.parameter_id,
            )
            del_result = await self.db.execute(del_stmt)
            old_chars = del_result.scalars().all()
            for old in old_chars:
                if old.is_locked:
                    continue
                await self.db.delete(old)
                deleted += 1
            await self.db.flush()

            if param.value_type == "enum" and item.parameter_value_ids:
                for pv_id in item.parameter_value_ids:
                    char = ProductCharacteristic(
                        product_id=product_id,
                        parameter_id=item.parameter_id,
                        parameter_value_id=pv_id,
                        source_type="manual",
                    )
                    self.db.add(char)
                    created += 1
            else:
                char = ProductCharacteristic(
                    product_id=product_id,
                    parameter_id=item.parameter_id,
                    value_text=item.value_text,
                    value_number=item.value_number,
                    value_bool=item.value_bool,
                    uom_id=item.uom_id,
                    source_type="manual",
                )
                self.db.add(char)
                created += 1

        await self.db.flush()
        return {"created": created, "updated": updated, "deleted": deleted}

    @transactional
    async def delete_characteristic(
        self, product_id: UUID, parameter_id: UUID, tenant_id: UUID,
    ) -> None:
        await self._verify_product(product_id, tenant_id)
        stmt = select(ProductCharacteristic).where(
            ProductCharacteristic.product_id == product_id,
            ProductCharacteristic.parameter_id == parameter_id,
        )
        result = await self.db.execute(stmt)
        chars = result.scalars().all()
        if not chars:
            raise NotFoundError("ProductCharacteristic", parameter_id)
        for char in chars:
            if char.is_locked:
                raise ValidationError("This characteristic is locked and cannot be deleted")
            await self.db.delete(char)
        await self.db.flush()

    async def _ensure_enum_value(self, parameter_id: UUID, label: str) -> UUID:
        """Find or auto-create a ParameterValue for the given enum label."""
        stmt = select(ParameterValue).where(
            ParameterValue.parameter_id == parameter_id,
            ParameterValue.label == label,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            return existing.id

        max_stmt = select(func.max(ParameterValue.sort_order)).where(
            ParameterValue.parameter_id == parameter_id,
        )
        max_order = (await self.db.execute(max_stmt)).scalar() or 0

        val_slug = _generate_slug(label)
        val_slug = await _ensure_unique_slug(
            self.db, ParameterValue, val_slug,
            [ParameterValue.parameter_id == parameter_id],
        )

        pv = ParameterValue(
            parameter_id=parameter_id,
            label=label,
            slug=val_slug,
            sort_order=max_order + 1,
        )
        self.db.add(pv)
        await self.db.flush()
        return pv.id
