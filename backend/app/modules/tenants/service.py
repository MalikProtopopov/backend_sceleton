"""Tenant service layer - business logic for tenants and feature flags."""

import json
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.tenants.models import (
    AVAILABLE_FEATURES,
    FeatureFlag,
    Tenant,
    TenantDomain,
    TenantSettings,
    get_feature_description,
)
from app.modules.tenants.schemas import (
    FeatureFlagCreate,
    FeatureFlagUpdate,
    TenantCreate,
    TenantDomainCreate,
    TenantDomainUpdate,
    TenantSettingsUpdate,
    TenantUpdate,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


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
        
        Invalidates Redis caches:
        - tenant_status_cache when is_active changes
        - domain_tenant_cache when any by-domain-visible field changes
          (name, logo_url, primary_color, is_active)
        """
        tenant = await self.get_by_id(tenant_id)
        tenant.check_version(data.version)

        update_data = data.model_dump(exclude_unset=True, exclude={"version"})
        is_active_changed = "is_active" in update_data

        # Fields that are returned by GET /public/tenants/by-domain/{domain}
        domain_visible_fields = {"name", "logo_url", "primary_color", "is_active"}
        domain_cache_dirty = bool(domain_visible_fields & update_data.keys())

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
            from app.core.redis import get_cors_origins_cache, get_tenant_status_cache
            cache = await get_tenant_status_cache()
            if cache:
                await cache.invalidate(str(tenant_id))
            get_cors_origins_cache().invalidate()

        # Invalidate domain_tenant_cache so by-domain resolution picks up
        # changes to name, primary_color, logo_url, is_active immediately.
        if domain_cache_dirty:
            from app.core.redis import get_domain_tenant_cache

            cache = await get_domain_tenant_cache()
            if cache:
                stmt = select(TenantDomain.domain).where(TenantDomain.tenant_id == tenant_id)
                result = await self.db.execute(stmt)
                for (domain_str,) in result.all():
                    await cache.invalidate(domain_str)

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

        # Invalidate tenant status cache + CORS origins
        from app.core.redis import get_cors_origins_cache, get_tenant_status_cache
        cache = await get_tenant_status_cache()
        if cache:
            await cache.invalidate(str(tenant_id))
        get_cors_origins_cache().invalidate()

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

    @transactional
    async def update_settings(
        self, tenant_id: UUID, data: TenantSettingsUpdate
    ) -> TenantSettings:
        """Update tenant settings.

        Handles encryption of sensitive fields (smtp_password, email_api_key)
        before persisting to database.
        """
        from app.core.encryption import get_encryption_service

        tenant = await self.get_by_id(tenant_id)
        enc = get_encryption_service()

        # Extract and encrypt sensitive write-only fields
        update_data = data.model_dump(exclude_unset=True)
        smtp_password = update_data.pop("smtp_password", None)
        email_api_key = update_data.pop("email_api_key", None)

        if not tenant.settings:
            # Create settings if not exists
            settings = TenantSettings(tenant_id=tenant_id, **update_data)
            self.db.add(settings)
        else:
            # Update existing settings
            for field, value in update_data.items():
                setattr(tenant.settings, field, value)
            settings = tenant.settings

        # Handle smtp_password: encrypt if provided, clear if explicitly set to empty/None
        if smtp_password is not None:
            if smtp_password:
                settings.smtp_password_encrypted = enc.encrypt(smtp_password)
            else:
                settings.smtp_password_encrypted = None
        # If smtp_password was not in the request at all, don't touch existing value

        # Handle email_api_key: encrypt if provided, clear if explicitly set to empty/None
        if email_api_key is not None:
            if email_api_key:
                settings.email_api_key_encrypted = enc.encrypt(email_api_key)
            else:
                settings.email_api_key_encrypted = None

        await self.db.flush()
        await self.db.refresh(settings)

        if "site_url" in update_data:
            from app.core.redis import get_cors_origins_cache
            get_cors_origins_cache().invalidate()

        return settings


    @transactional
    async def update_logo_url(self, tenant_id: UUID, url: str | None) -> Tenant:
        """Update or clear the tenant logo URL."""
        tenant = await self.get_by_id(tenant_id)
        tenant.logo_url = url
        await self.db.flush()
        await self.db.refresh(tenant)
        return tenant


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


class TenantDomainService:
    """Service for tenant domain CRUD and resolution (domain → tenant)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public resolve (used by GET /public/tenants/by-domain/{domain})
    # ------------------------------------------------------------------

    async def resolve(self, domain: str) -> dict | None:
        """Resolve a domain to tenant info dict.

        Returns cached result from Redis when available.
        On cache miss queries DB and stores in Redis for 5 min.
        Returns ``None`` if the domain is not registered.
        """
        domain = domain.strip().lower()

        # 1. Try Redis cache
        from app.core.redis import get_domain_tenant_cache

        cache = await get_domain_tenant_cache()
        if cache:
            cached = await cache.get(domain)
            if cached is not None:
                return json.loads(cached)

        # 2. DB lookup
        stmt = (
            select(TenantDomain)
            .where(TenantDomain.domain == domain)
            .options(selectinload(TenantDomain.tenant).selectinload(Tenant.settings))
        )
        result = await self.db.execute(stmt)
        td = result.scalar_one_or_none()

        if td is None or td.tenant is None:
            return None

        tenant = td.tenant
        if tenant.deleted_at is not None or not tenant.is_active:
            return None

        site_url = None
        if tenant.settings and tenant.settings.site_url:
            site_url = tenant.settings.site_url

        data = {
            "tenant_id": str(tenant.id),
            "slug": tenant.slug,
            "name": tenant.name,
            "logo_url": tenant.logo_url,
            "primary_color": tenant.primary_color,
            "site_url": site_url,
        }

        # 3. Store in cache
        if cache:
            await cache.set(domain, json.dumps(data))

        return data

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def list_domains(self, tenant_id: UUID) -> list[TenantDomain]:
        """List all domains for a tenant."""
        stmt = (
            select(TenantDomain)
            .where(TenantDomain.tenant_id == tenant_id)
            .order_by(TenantDomain.is_primary.desc(), TenantDomain.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_domain(self, domain_id: UUID) -> TenantDomain:
        """Get a single domain by ID (for status checks)."""
        return await self._get_by_id(domain_id)

    @transactional
    async def add_domain(self, tenant_id: UUID, data: TenantDomainCreate) -> TenantDomain:
        """Attach a new domain to a tenant.

        After creation, enqueues a background task to verify DNS
        and provision an SSL certificate via Caddy.
        """
        # Verify tenant exists
        tenant_stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.deleted_at.is_(None))
        if not (await self.db.execute(tenant_stmt)).scalar_one_or_none():
            raise NotFoundError("Tenant", tenant_id)

        # Check uniqueness
        existing = await self.db.execute(
            select(TenantDomain).where(TenantDomain.domain == data.domain)
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsError("TenantDomain", "domain", data.domain)

        # If is_primary, un-primary others
        if data.is_primary:
            await self._unset_primary(tenant_id)

        td = TenantDomain(tenant_id=tenant_id, **data.model_dump())
        self.db.add(td)
        await self.db.flush()
        await self.db.refresh(td)

        self._invalidate_cors_cache()

        # Enqueue background SSL provisioning
        try:
            from app.tasks.domain_tasks import provision_domain_task
            await provision_domain_task.kiq(str(td.id))
        except Exception:
            pass  # Don't fail domain creation if task queue is unavailable

        return td

    @transactional
    async def update_domain(self, domain_id: UUID, data: TenantDomainUpdate) -> TenantDomain:
        """Update domain attributes (is_primary, ssl_status)."""
        td = await self._get_by_id(domain_id)
        update = data.model_dump(exclude_unset=True)

        if update.get("is_primary"):
            await self._unset_primary(td.tenant_id)

        for field, value in update.items():
            setattr(td, field, value)

        await self.db.flush()
        await self.db.refresh(td)

        await self._invalidate_cache(td.domain)
        self._invalidate_cors_cache()
        return td

    @transactional
    async def remove_domain(self, domain_id: UUID) -> None:
        """Remove a domain binding."""
        td = await self._get_by_id(domain_id)
        domain_str = td.domain
        await self.db.delete(td)
        await self.db.flush()

        await self._invalidate_cache(domain_str)
        self._invalidate_cors_cache()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def get_primary_domain(self, tenant_id: UUID) -> str | None:
        """Return the primary domain string for a tenant, or None."""
        stmt = (
            select(TenantDomain.domain)
            .where(TenantDomain.tenant_id == tenant_id, TenantDomain.is_primary.is_(True))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_by_id(self, domain_id: UUID) -> TenantDomain:
        td = (await self.db.execute(
            select(TenantDomain).where(TenantDomain.id == domain_id)
        )).scalar_one_or_none()
        if td is None:
            raise NotFoundError("TenantDomain", domain_id)
        return td

    async def _unset_primary(self, tenant_id: UUID) -> None:
        """Remove is_primary from all existing domains of the tenant."""
        stmt = (
            select(TenantDomain)
            .where(TenantDomain.tenant_id == tenant_id, TenantDomain.is_primary.is_(True))
        )
        result = await self.db.execute(stmt)
        for existing in result.scalars():
            existing.is_primary = False

    async def _invalidate_cache(self, domain: str) -> None:
        from app.core.redis import get_domain_tenant_cache

        cache = await get_domain_tenant_cache()
        if cache:
            await cache.invalidate(domain)

    @staticmethod
    def _invalidate_cors_cache() -> None:
        from app.core.redis import get_cors_origins_cache
        get_cors_origins_cache().invalidate()

