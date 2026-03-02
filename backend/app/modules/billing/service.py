"""Billing services: module access, plan management, limits, upgrade requests."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transactional
from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.core.logging import get_logger
from app.modules.billing.models import (
    BillingModule,
    Bundle,
    BundleModule,
    Plan,
    PlanModule,
    TenantModule,
    TenantModuleSource,
    UpgradeRequest,
    UpgradeRequestStatus,
    UpgradeRequestType,
)

logger = get_logger(__name__)

_FLAG_TO_MODULE: dict[str, str] = {
    "blog_module": "content",
    "cases_module": "content",
    "reviews_module": "content",
    "faq_module": "content",
    "team_module": "company",
    "services_module": "company",
    "analytics_advanced": "crm_pro",
    "seo_advanced": "seo_advanced",
    "multilang": "multilang",
    "catalog_module": "catalog_basic",
    "variants_module": "catalog_pro",
}


class LimitStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    EXCEEDED = "exceeded"
    NOT_AVAILABLE = "not_available"


class ModuleAccessService:
    """Check whether a billing module is enabled for a tenant.

    Accepts both legacy feature-flag names (e.g. ``blog_module``) and
    new billing module slugs (e.g. ``content``).  Legacy names are mapped
    to their billing-module slug via ``_FLAG_TO_MODULE``.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def is_enabled(self, tenant_id: UUID, feature_or_module: str) -> bool:
        module_slug = _FLAG_TO_MODULE.get(feature_or_module, feature_or_module)

        stmt = (
            select(TenantModule.enabled)
            .join(BillingModule, TenantModule.module_id == BillingModule.id)
            .where(
                TenantModule.tenant_id == tenant_id,
                BillingModule.slug == module_slug,
                TenantModule.enabled.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        row = result.first()
        return row is not None

    async def get_enabled_module_slugs(self, tenant_id: UUID) -> set[str]:
        stmt = (
            select(BillingModule.slug)
            .join(TenantModule, TenantModule.module_id == BillingModule.id)
            .where(
                TenantModule.tenant_id == tenant_id,
                TenantModule.enabled.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}


class PlanService:
    """CRUD and business logic for plans, modules, bundles."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Module queries ──

    async def list_modules(self) -> list[BillingModule]:
        stmt = select(BillingModule).order_by(BillingModule.sort_order)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_module_by_slug(self, slug: str) -> BillingModule:
        stmt = select(BillingModule).where(BillingModule.slug == slug)
        result = await self.db.execute(stmt)
        mod = result.scalar_one_or_none()
        if not mod:
            raise NotFoundError("BillingModule", slug)
        return mod

    async def get_module_by_id(self, module_id: UUID) -> BillingModule:
        stmt = select(BillingModule).where(BillingModule.id == module_id)
        result = await self.db.execute(stmt)
        mod = result.scalar_one_or_none()
        if not mod:
            raise NotFoundError("BillingModule", str(module_id))
        return mod

    @transactional
    async def create_module(self, data: dict) -> BillingModule:
        mod = BillingModule(**data)
        self.db.add(mod)
        await self.db.flush()
        await self.db.refresh(mod)
        return mod

    @transactional
    async def update_module(self, module_id: UUID, data: dict) -> BillingModule:
        mod = await self.get_module_by_id(module_id)
        for k, v in data.items():
            if v is not None:
                setattr(mod, k, v)
        await self.db.flush()
        await self.db.refresh(mod)
        return mod

    # ── Plan queries ──

    async def list_plans(self, active_only: bool = True) -> list[Plan]:
        stmt = select(Plan).options(selectinload(Plan.module_links).selectinload(PlanModule.module))
        if active_only:
            stmt = stmt.where(Plan.is_active.is_(True))
        stmt = stmt.order_by(Plan.sort_order)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_plan_by_slug(self, slug: str) -> Plan:
        stmt = (
            select(Plan)
            .options(selectinload(Plan.module_links).selectinload(PlanModule.module))
            .where(Plan.slug == slug)
        )
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError("Plan", slug)
        return plan

    async def get_plan_by_id(self, plan_id: UUID) -> Plan:
        stmt = (
            select(Plan)
            .options(selectinload(Plan.module_links).selectinload(PlanModule.module))
            .where(Plan.id == plan_id)
        )
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError("Plan", str(plan_id))
        return plan

    async def get_default_plan(self) -> Plan:
        stmt = (
            select(Plan)
            .options(selectinload(Plan.module_links).selectinload(PlanModule.module))
            .where(Plan.is_default.is_(True))
        )
        result = await self.db.execute(stmt)
        plan = result.scalar_one_or_none()
        if not plan:
            raise NotFoundError("Plan", "default")
        return plan

    @transactional
    async def create_plan(self, data: dict, module_slugs: list[str] | None = None) -> Plan:
        plan_data = {k: v for k, v in data.items() if k != "module_slugs"}
        plan = Plan(**plan_data)
        self.db.add(plan)
        await self.db.flush()

        if module_slugs:
            await self._set_plan_modules(plan.id, module_slugs)

        await self.db.refresh(plan)
        return plan

    @transactional
    async def update_plan(self, plan_id: UUID, data: dict, module_slugs: list[str] | None = None) -> Plan:
        plan = await self.get_plan_by_id(plan_id)
        for k, v in data.items():
            if v is not None and k != "module_slugs":
                setattr(plan, k, v)
        await self.db.flush()

        if module_slugs is not None:
            await self._set_plan_modules(plan.id, module_slugs)

        await self.db.refresh(plan)
        return plan

    async def _set_plan_modules(self, plan_id: UUID, module_slugs: list[str]) -> None:
        await self.db.execute(
            delete(PlanModule).where(PlanModule.plan_id == plan_id)
        )
        for slug in module_slugs:
            mod = await self.get_module_by_slug(slug)
            self.db.add(PlanModule(plan_id=plan_id, module_id=mod.id))
        await self.db.flush()

    # ── Bundle queries ──

    async def list_bundles(self, active_only: bool = True) -> list[Bundle]:
        stmt = select(Bundle).options(selectinload(Bundle.module_links).selectinload(BundleModule.module))
        if active_only:
            stmt = stmt.where(Bundle.is_active.is_(True))
        stmt = stmt.order_by(Bundle.sort_order)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_bundle_by_id(self, bundle_id: UUID) -> Bundle:
        stmt = (
            select(Bundle)
            .options(selectinload(Bundle.module_links).selectinload(BundleModule.module))
            .where(Bundle.id == bundle_id)
        )
        result = await self.db.execute(stmt)
        bundle = result.scalar_one_or_none()
        if not bundle:
            raise NotFoundError("Bundle", str(bundle_id))
        return bundle

    @transactional
    async def create_bundle(self, data: dict, module_slugs: list[str] | None = None) -> Bundle:
        bundle_data = {k: v for k, v in data.items() if k != "module_slugs"}
        bundle = Bundle(**bundle_data)
        self.db.add(bundle)
        await self.db.flush()

        if module_slugs:
            await self._set_bundle_modules(bundle.id, module_slugs)

        await self.db.refresh(bundle)
        return bundle

    @transactional
    async def update_bundle(self, bundle_id: UUID, data: dict, module_slugs: list[str] | None = None) -> Bundle:
        bundle = await self.get_bundle_by_id(bundle_id)
        for k, v in data.items():
            if v is not None and k != "module_slugs":
                setattr(bundle, k, v)
        await self.db.flush()

        if module_slugs is not None:
            await self._set_bundle_modules(bundle.id, module_slugs)

        await self.db.refresh(bundle)
        return bundle

    async def _set_bundle_modules(self, bundle_id: UUID, module_slugs: list[str]) -> None:
        await self.db.execute(
            delete(BundleModule).where(BundleModule.bundle_id == bundle_id)
        )
        for slug in module_slugs:
            mod = await self.get_module_by_slug(slug)
            self.db.add(BundleModule(bundle_id=bundle_id, module_id=mod.id))
        await self.db.flush()

    # ── Tenant module management ──

    async def get_tenant_modules(self, tenant_id: UUID) -> list[TenantModule]:
        stmt = (
            select(TenantModule)
            .options(selectinload(TenantModule.module))
            .where(TenantModule.tenant_id == tenant_id)
            .order_by(TenantModule.activated_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def get_tenant_modules_for_tenant(self, tenant_id: UUID) -> list[TenantModule]:
        result = await self.db.execute(
            select(TenantModule)
            .options(selectinload(TenantModule.module))
            .where(TenantModule.tenant_id == tenant_id)
            .order_by(TenantModule.activated_at)
        )
        return list(result.scalars().all())

    @transactional
    async def add_tenant_module(
        self,
        tenant_id: UUID,
        module_slug: str,
        source: str = TenantModuleSource.MANUAL.value,
    ) -> TenantModule:
        mod = await self.get_module_by_slug(module_slug)
        existing = await self.db.execute(
            select(TenantModule).where(
                TenantModule.tenant_id == tenant_id,
                TenantModule.module_id == mod.id,
            )
        )
        if existing.scalar_one_or_none():
            raise AlreadyExistsError("TenantModule", "module_slug", module_slug)

        tm = TenantModule(
            tenant_id=tenant_id,
            module_id=mod.id,
            source=source,
            enabled=True,
        )
        self.db.add(tm)
        await self.db.flush()
        await self.db.refresh(tm, ["module"])
        return tm

    @transactional
    async def remove_tenant_module(self, tenant_id: UUID, module_slug: str) -> None:
        mod = await self.get_module_by_slug(module_slug)
        await self.db.execute(
            delete(TenantModule).where(
                TenantModule.tenant_id == tenant_id,
                TenantModule.module_id == mod.id,
            )
        )

    @transactional
    async def set_module_enabled(
        self, tenant_id: UUID, module_slug: str, enabled: bool
    ) -> None:
        """Set enabled state for a tenant's module. Used when syncing from feature_flags."""
        mod = await self.get_module_by_slug(module_slug)
        stmt = (
            select(TenantModule)
            .where(TenantModule.tenant_id == tenant_id)
            .where(TenantModule.module_id == mod.id)
        )
        result = await self.db.execute(stmt)
        tm = result.scalar_one_or_none()
        if tm:
            tm.enabled = enabled
            await self.db.flush()
        elif enabled:
            self.db.add(
                TenantModule(
                    tenant_id=tenant_id,
                    module_id=mod.id,
                    source=TenantModuleSource.MANUAL.value,
                    enabled=True,
                )
            )
            await self.db.flush()

    @transactional
    async def set_plan_for_tenant(self, tenant_id: UUID, plan: Plan) -> None:
        """Replace plan-sourced modules with those from the new plan.

        Addon/bundle/manual modules are *preserved*.
        """
        from app.modules.tenants.models import Tenant

        # Delete only plan-sourced modules
        await self.db.execute(
            delete(TenantModule).where(
                TenantModule.tenant_id == tenant_id,
                TenantModule.source == TenantModuleSource.PLAN.value,
            )
        )
        # Create new plan-sourced modules
        for link in plan.module_links:
            self.db.add(TenantModule(
                tenant_id=tenant_id,
                module_id=link.module_id,
                source=TenantModuleSource.PLAN.value,
                enabled=True,
            ))
        # Update tenant.plan_id
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one()
        tenant.plan_id = plan.id
        await self.db.flush()

    @transactional
    async def activate_bundle_for_tenant(self, tenant_id: UUID, bundle: Bundle) -> None:
        for link in bundle.module_links:
            existing = await self.db.execute(
                select(TenantModule).where(
                    TenantModule.tenant_id == tenant_id,
                    TenantModule.module_id == link.module_id,
                    TenantModule.source == TenantModuleSource.BUNDLE.value,
                )
            )
            if not existing.scalar_one_or_none():
                self.db.add(TenantModule(
                    tenant_id=tenant_id,
                    module_id=link.module_id,
                    source=TenantModuleSource.BUNDLE.value,
                    enabled=True,
                ))
        await self.db.flush()


class LimitService:
    """Check and report resource usage against plan limits."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_limits(self, tenant_id: UUID) -> dict[str, int | None]:
        """Return the plan limits dict for a tenant. None values = unlimited."""
        from app.modules.tenants.models import Tenant

        stmt = (
            select(Tenant)
            .options(selectinload(Tenant.plan))
            .where(Tenant.id == tenant_id)
        )
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        if not tenant or not tenant.plan:
            return {}
        raw = tenant.plan.limits or {}
        out: dict[str, int | None] = {}
        for k, v in raw.items():
            out[k] = None if v == -1 else v
        return out

    async def get_usage(self, tenant_id: UUID) -> dict[str, int]:
        from app.modules.auth.models import AdminUser, Role
        from app.modules.media.models import FileAsset
        from app.modules.leads.models import Inquiry
        from app.modules.catalog.models import Product
        from app.modules.variants.models import ProductVariant
        from app.modules.tenants.models import TenantDomain
        from app.modules.content.models import Article

        queries: dict[str, any] = {
            "max_users": select(func.count()).select_from(AdminUser).where(
                AdminUser.tenant_id == tenant_id, AdminUser.deleted_at.is_(None)
            ),
            "max_storage_mb": select(
                func.coalesce(func.sum(FileAsset.file_size), 0)
            ).where(FileAsset.tenant_id == tenant_id),
            "max_leads_per_month": select(func.count()).select_from(Inquiry).where(
                Inquiry.tenant_id == tenant_id,
                Inquiry.created_at >= func.date_trunc("month", func.now()),
            ),
            "max_products": select(func.count()).select_from(Product).where(
                Product.tenant_id == tenant_id
            ),
            "max_variants": select(func.count()).select_from(ProductVariant).where(
                ProductVariant.tenant_id == tenant_id
            ),
            "max_domains": select(func.count()).select_from(TenantDomain).where(
                TenantDomain.tenant_id == tenant_id
            ),
            "max_articles": select(func.count()).select_from(Article).where(
                Article.tenant_id == tenant_id
            ),
            "max_rbac_roles": select(func.count()).select_from(Role).where(
                Role.tenant_id == tenant_id
            ),
        }

        usage: dict[str, int] = {}
        for resource, stmt in queries.items():
            result = await self.db.execute(stmt)
            val = result.scalar() or 0
            if resource == "max_storage_mb":
                val = val // (1024 * 1024)  # bytes -> MB
            usage[resource] = val

        return usage

    async def check_limit(self, tenant_id: UUID, resource: str) -> LimitStatus:
        limits = await self.get_limits(tenant_id)
        limit_val = limits.get(resource)
        if limit_val is None:
            return LimitStatus.OK

        usage = await self.get_usage(tenant_id)
        current = usage.get(resource, 0)

        if current >= limit_val:
            return LimitStatus.EXCEEDED
        if limit_val > 0 and current >= limit_val * 0.8:
            return LimitStatus.WARNING
        return LimitStatus.OK

    async def get_full_usage_report(self, tenant_id: UUID) -> dict[str, dict]:
        limits = await self.get_limits(tenant_id)
        usage = await self.get_usage(tenant_id)

        report: dict[str, dict] = {}
        all_keys = set(limits.keys()) | set(usage.keys())
        for key in all_keys:
            limit_val = limits.get(key)
            current = usage.get(key, 0)
            if limit_val is None:
                status = LimitStatus.OK
            elif limit_val == 0:
                status = LimitStatus.NOT_AVAILABLE
            elif current >= limit_val:
                status = LimitStatus.EXCEEDED
            elif limit_val > 0 and current >= limit_val * 0.8:
                status = LimitStatus.WARNING
            else:
                status = LimitStatus.OK
            report[key] = {
                "current": current,
                "limit": limit_val,
                "status": status.value,
            }
        return report


class UpgradeRequestService:
    """CRUD and approval logic for upgrade requests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_requests(
        self,
        tenant_id: UUID | None = None,
        status: str | None = None,
    ) -> list[UpgradeRequest]:
        stmt = select(UpgradeRequest).order_by(UpgradeRequest.created_at.desc())
        if tenant_id:
            stmt = stmt.where(UpgradeRequest.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(UpgradeRequest.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    @transactional
    async def create_request(self, tenant_id: UUID, data: dict) -> UpgradeRequest:
        req = UpgradeRequest(tenant_id=tenant_id, **data)
        self.db.add(req)
        await self.db.flush()
        await self.db.refresh(req)
        return req

    async def get_request(self, request_id: UUID) -> UpgradeRequest:
        stmt = select(UpgradeRequest).where(UpgradeRequest.id == request_id)
        result = await self.db.execute(stmt)
        req = result.scalar_one_or_none()
        if not req:
            raise NotFoundError("UpgradeRequest", str(request_id))
        return req

    @transactional
    async def approve(self, request_id: UUID, reviewer_id: UUID) -> UpgradeRequest:
        req = await self.get_request(request_id)
        req.status = UpgradeRequestStatus.APPROVED.value
        req.reviewed_by = reviewer_id
        req.reviewed_at = datetime.now(UTC)

        plan_svc = PlanService(self.db)

        if req.request_type == UpgradeRequestType.PLAN_UPGRADE.value:
            if not req.target_plan_id:
                raise NotFoundError("Plan", "target_plan_id is null")
            plan = await plan_svc.get_plan_by_id(req.target_plan_id)
            await plan_svc.set_plan_for_tenant(req.tenant_id, plan)

        elif req.request_type == UpgradeRequestType.MODULE_ADDON.value:
            if not req.target_module_id:
                raise NotFoundError("BillingModule", "target_module_id is null")
            mod = await plan_svc.get_module_by_id(req.target_module_id)
            try:
                await plan_svc.add_tenant_module(
                    req.tenant_id, mod.slug, source=TenantModuleSource.ADDON.value
                )
            except AlreadyExistsError:
                pass  # already active — no-op

        elif req.request_type == UpgradeRequestType.BUNDLE_ADDON.value:
            if not req.target_bundle_id:
                raise NotFoundError("Bundle", "target_bundle_id is null")
            bundle = await plan_svc.get_bundle_by_id(req.target_bundle_id)
            await plan_svc.activate_bundle_for_tenant(req.tenant_id, bundle)

        await self.db.flush()
        await self.db.refresh(req)

        logger.info(
            "upgrade_request_approved",
            request_id=str(req.id),
            tenant_id=str(req.tenant_id),
            type=req.request_type,
        )

        # Best-effort notification
        try:
            from app.modules.billing.notifications import notify_upgrade_request_reviewed
            await notify_upgrade_request_reviewed(
                self.db, req.tenant_id, "approved", req.request_type
            )
        except Exception:
            pass

        return req

    @transactional
    async def reject(self, request_id: UUID, reviewer_id: UUID) -> UpgradeRequest:
        req = await self.get_request(request_id)
        req.status = UpgradeRequestStatus.REJECTED.value
        req.reviewed_by = reviewer_id
        req.reviewed_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(req)

        try:
            from app.modules.billing.notifications import notify_upgrade_request_reviewed
            await notify_upgrade_request_reviewed(
                self.db, req.tenant_id, "rejected", req.request_type
            )
        except Exception:
            pass

        return req
