"""Tenant service layer - business logic for tenants and feature flags."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.tenants.models import AVAILABLE_FEATURES, FeatureFlag, Tenant, TenantSettings
from app.modules.tenants.schemas import (
    FeatureFlagCreate,
    FeatureFlagUpdate,
    TenantCreate,
    TenantSettingsUpdate,
    TenantUpdate,
)


class TenantService:
    """Service for tenant operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, tenant_id: UUID) -> Tenant:
        """Get tenant by ID."""
        stmt = (
            select(Tenant)
            .where(Tenant.id == tenant_id)
            .where(Tenant.deleted_at.is_(None))
            .options(selectinload(Tenant.settings))
        )
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        return tenant

    async def get_by_slug(self, slug: str) -> Tenant:
        """Get tenant by slug."""
        stmt = (
            select(Tenant)
            .where(Tenant.slug == slug)
            .where(Tenant.deleted_at.is_(None))
            .options(selectinload(Tenant.settings))
        )
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise NotFoundError("Tenant", slug)

        return tenant

    async def list_tenants(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination."""
        # Base query
        base_query = select(Tenant).where(Tenant.deleted_at.is_(None))

        if is_active is not None:
            base_query = base_query.where(Tenant.is_active == is_active)

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Get paginated results
        stmt = (
            base_query.options(selectinload(Tenant.settings))
            .order_by(Tenant.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        tenants = list(result.scalars().all())

        return tenants, total

    @transactional
    async def create(self, data: TenantCreate) -> Tenant:
        """Create a new tenant."""
        # Check slug uniqueness
        existing = await self.db.execute(
            select(Tenant).where(Tenant.slug == data.slug).where(Tenant.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsError("Tenant", "slug", data.slug)

        # Create tenant
        tenant = Tenant(**data.model_dump())
        self.db.add(tenant)
        await self.db.flush()

        # Create default settings
        settings = TenantSettings(tenant_id=tenant.id)
        self.db.add(settings)

        # Create default feature flags
        for feature_name, description in AVAILABLE_FEATURES.items():
            flag = FeatureFlag(
                tenant_id=tenant.id,
                feature_name=feature_name,
                enabled=False,
                description=description,
            )
            self.db.add(flag)

        await self.db.flush()
        await self.db.refresh(tenant)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(tenant, ["settings", "feature_flags"])

        return tenant

    @transactional
    async def update(self, tenant_id: UUID, data: TenantUpdate) -> Tenant:
        """Update tenant with optimistic locking."""
        tenant = await self.get_by_id(tenant_id)
        tenant.check_version(data.version)

        # Update fields
        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        for field, value in update_data.items():
            setattr(tenant, field, value)

        await self.db.flush()
        await self.db.refresh(tenant)

        return tenant

    @transactional
    async def soft_delete(self, tenant_id: UUID) -> None:
        """Soft delete a tenant."""
        tenant = await self.get_by_id(tenant_id)
        tenant.soft_delete()
        await self.db.flush()

    async def update_settings(
        self, tenant_id: UUID, data: TenantSettingsUpdate
    ) -> TenantSettings:
        """Update tenant settings."""
        tenant = await self.get_by_id(tenant_id)

        if not tenant.settings:
            # Create settings if not exists
            settings = TenantSettings(tenant_id=tenant_id, **data.model_dump())
            self.db.add(settings)
        else:
            # Update existing settings
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(tenant.settings, field, value)
            settings = tenant.settings

        await self.db.commit()
        await self.db.refresh(settings)

        return settings


class FeatureFlagService:
    """Service for feature flag operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_flags(self, tenant_id: UUID) -> list[FeatureFlag]:
        """Get all feature flags for a tenant."""
        stmt = select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def is_enabled(self, tenant_id: UUID, feature_name: str) -> bool:
        """Check if a feature is enabled for a tenant.

        Usage:
            if await feature_service.is_enabled(tenant_id, "cases_module"):
                # Feature is enabled
        """
        stmt = (
            select(FeatureFlag.enabled)
            .where(FeatureFlag.tenant_id == tenant_id)
            .where(FeatureFlag.feature_name == feature_name)
        )
        result = await self.db.execute(stmt)
        enabled = result.scalar_one_or_none()

        return enabled is True

    @transactional
    async def update_flag(
        self, tenant_id: UUID, feature_name: str, data: FeatureFlagUpdate
    ) -> FeatureFlag:
        """Update a feature flag."""
        stmt = (
            select(FeatureFlag)
            .where(FeatureFlag.tenant_id == tenant_id)
            .where(FeatureFlag.feature_name == feature_name)
        )
        result = await self.db.execute(stmt)
        flag = result.scalar_one_or_none()

        if not flag:
            raise NotFoundError("FeatureFlag", feature_name)

        flag.enabled = data.enabled
        await self.db.flush()
        await self.db.refresh(flag)

        return flag

    @transactional
    async def create_flag(self, tenant_id: UUID, data: FeatureFlagCreate) -> FeatureFlag:
        """Create a new feature flag."""
        # Check if flag already exists
        stmt = (
            select(FeatureFlag)
            .where(FeatureFlag.tenant_id == tenant_id)
            .where(FeatureFlag.feature_name == data.feature_name)
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise AlreadyExistsError("FeatureFlag", "feature_name", data.feature_name)

        flag = FeatureFlag(tenant_id=tenant_id, **data.model_dump())
        self.db.add(flag)
        await self.db.flush()
        await self.db.refresh(flag)

        return flag

