"""Tenant service layer - business logic for tenants and feature flags."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.tenants.models import AVAILABLE_FEATURES, FeatureFlag, Tenant, TenantSettings, get_feature_description
from app.modules.tenants.schemas import (
    FeatureFlagCreate,
    FeatureFlagUpdate,
    TenantCreate,
    TenantSettingsUpdate,
    TenantUpdate,
)


class TenantService:
    """Service for tenant operations."""

    def __init__(self, db: AsyncSession, actor_id: UUID | None = None) -> None:
        self.db = db
        self._actor_id = actor_id
        self._audit_svc = None

    @property
    def _audit(self):
        if self._audit_svc is None:
            from app.core.audit import AuditService
            self._audit_svc = AuditService(self.db)
        return self._audit_svc

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
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Tenant], int]:
        """List tenants with pagination, optional search, sorting, and users_count."""
        from app.modules.auth.models import AdminUser

        # Base query
        base_query = select(Tenant).where(Tenant.deleted_at.is_(None))

        if is_active is not None:
            base_query = base_query.where(Tenant.is_active == is_active)

        if search:
            search_pattern = f"%{search}%"
            base_query = base_query.where(Tenant.name.ilike(search_pattern))

        # Count total
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Determine sort column
        sort_columns = {
            "name": Tenant.name,
            "created_at": Tenant.created_at,
        }
        sort_col = sort_columns.get(sort_by, Tenant.created_at)
        order_clause = sort_col.asc() if sort_order == "asc" else sort_col.desc()

        # Get paginated results
        stmt = (
            base_query.options(selectinload(Tenant.settings))
            .order_by(order_clause)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        tenants = list(result.scalars().all())

        # Compute users_count for each tenant
        if tenants:
            tenant_ids = [t.id for t in tenants]
            counts_stmt = (
                select(AdminUser.tenant_id, func.count().label("cnt"))
                .where(
                    AdminUser.tenant_id.in_(tenant_ids),
                    AdminUser.deleted_at.is_(None),
                    AdminUser.is_active.is_(True),
                )
                .group_by(AdminUser.tenant_id)
            )
            counts_result = await self.db.execute(counts_stmt)
            counts_map = {row.tenant_id: row.cnt for row in counts_result}
            for tenant in tenants:
                tenant.users_count = counts_map.get(tenant.id, 0)  # type: ignore[attr-defined]
        
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

        # Create default feature flags (enabled=True by default for new tenants)
        for feature_name in AVAILABLE_FEATURES:
            flag = FeatureFlag(
                tenant_id=tenant.id,
                feature_name=feature_name,
                enabled=True,
                description=get_feature_description(feature_name),
            )
            self.db.add(flag)

        await self.db.flush()

        # Audit log: tenant created
        await self._audit.log(
            tenant_id=tenant.id,
            user_id=self._actor_id,
            resource_type="tenant",
            resource_id=tenant.id,
            action="create",
            changes={"name": tenant.name, "slug": tenant.slug},
        )

        await self.db.refresh(tenant)  # Full refresh for scalar fields (updated_at, etc.)
        await self.db.refresh(tenant, ["settings", "feature_flags"])

        return tenant

    @transactional
    async def update(self, tenant_id: UUID, data: TenantUpdate) -> Tenant:
        """Update tenant with optimistic locking.
        
        Invalidates Redis tenant status cache when is_active changes.
        """
        tenant = await self.get_by_id(tenant_id)
        tenant.check_version(data.version)

        # Track is_active change for cache invalidation
        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        is_active_changed = "is_active" in update_data

        # Track changes for audit log
        changes: dict = {}
        for field, value in update_data.items():
            old_value = getattr(tenant, field, None)
            if old_value != value:
                changes[field] = {"old": str(old_value) if old_value is not None else None, "new": str(value)}
            setattr(tenant, field, value)

        await self.db.flush()

        # Audit log: tenant updated
        if changes:
            await self._audit.log(
                tenant_id=tenant_id,
                user_id=self._actor_id,
                resource_type="tenant",
                resource_id=tenant_id,
                action="update",
                changes=changes,
            )

        await self.db.refresh(tenant)

        # Invalidate tenant status cache if is_active changed
        if is_active_changed:
            from app.core.redis import get_tenant_status_cache
            cache = await get_tenant_status_cache()
            if cache:
                await cache.invalidate(str(tenant_id))

        return tenant

    @transactional
    async def soft_delete(self, tenant_id: UUID) -> None:
        """Soft delete a tenant. Invalidates tenant status cache."""
        tenant = await self.get_by_id(tenant_id)
        tenant.soft_delete()
        await self.db.flush()

        # Audit log: tenant deleted
        await self._audit.log(
            tenant_id=tenant_id,
            user_id=self._actor_id,
            resource_type="tenant",
            resource_id=tenant_id,
            action="delete",
            changes={"name": tenant.name},
        )

        # Invalidate tenant status cache
        from app.core.redis import get_tenant_status_cache
        cache = await get_tenant_status_cache()
        if cache:
            await cache.invalidate(str(tenant_id))

    async def get_settings(self, tenant_id: UUID) -> TenantSettings | None:
        """Get tenant settings by tenant ID.
        
        Returns None if tenant or settings don't exist.
        """
        stmt = (
            select(TenantSettings)
            .where(TenantSettings.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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

    def __init__(self, db: AsyncSession, actor_id: UUID | None = None) -> None:
        self.db = db
        self._actor_id = actor_id
        self._audit_svc = None

    @property
    def _audit(self):
        if self._audit_svc is None:
            from app.core.audit import AuditService
            self._audit_svc = AuditService(self.db)
        return self._audit_svc

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

        old_enabled = flag.enabled
        flag.enabled = data.enabled
        await self.db.flush()

        # Audit log: feature flag toggled
        if old_enabled != data.enabled:
            await self._audit.log(
                tenant_id=tenant_id,
                user_id=self._actor_id,
                resource_type="feature_flag",
                resource_id=flag.id,
                action="update",
                changes={
                    "feature_name": feature_name,
                    "enabled": {"old": str(old_enabled), "new": str(data.enabled)},
                },
            )

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

