"""API routes for the billing module: plans, modules, bundles, tenant access, upgrades."""

from uuid import UUID

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_public_tenant_id
from app.core.exceptions import RateLimitExceededError
from app.core.redis import RateLimiter, get_redis
from app.core.security import (
    PermissionChecker,
    get_current_tenant_id,
    get_current_token,
    require_platform_owner,
    TokenPayload,
)
from app.modules.auth.models import AdminUser
from app.modules.billing.schemas import (
    BillingModuleCreate,
    BillingModuleResponse,
    BillingModuleUpdate,
    BundleCreate,
    BundleResponse,
    BundleUpdate,
    MyModulesResponse,
    MyPlanResponse,
    PlanCreate,
    PlanResponse,
    PlanUpdate,
    TenantModuleCreate,
    TenantModuleRemove,
    TenantModuleResponse,
    UpgradeRequestCreate,
    UpgradeRequestResponse,
    UpgradeRequestReview,
    UsageInfo,
)
from app.modules.billing.service import (
    LimitService,
    ModuleAccessService,
    PlanService,
    UpgradeRequestService,
)

router = APIRouter(tags=["Billing"])


# ============================================================================
# Helpers
# ============================================================================


def _plan_response(plan) -> PlanResponse:
    return PlanResponse(
        id=plan.id,
        slug=plan.slug,
        name=plan.name,
        name_ru=plan.name_ru,
        description=plan.description,
        description_ru=plan.description_ru,
        price_monthly_kopecks=plan.price_monthly_kopecks,
        price_yearly_kopecks=plan.price_yearly_kopecks,
        setup_fee_kopecks=plan.setup_fee_kopecks,
        is_default=plan.is_default,
        is_active=plan.is_active,
        sort_order=plan.sort_order,
        limits=plan.limits,
        modules=[
            {"id": m.id, "slug": m.slug, "name": m.name, "name_ru": m.name_ru,
             "category": m.category, "is_base": m.is_base}
            for m in plan.modules
        ],
    )


def _bundle_response(bundle) -> BundleResponse:
    return BundleResponse(
        id=bundle.id,
        slug=bundle.slug,
        name=bundle.name,
        name_ru=bundle.name_ru,
        description=bundle.description,
        description_ru=bundle.description_ru,
        price_monthly_kopecks=bundle.price_monthly_kopecks,
        discount_percent=bundle.discount_percent,
        is_active=bundle.is_active,
        sort_order=bundle.sort_order,
        modules=[
            {"id": m.id, "slug": m.slug, "name": m.name, "name_ru": m.name_ru}
            for m in bundle.modules
        ],
    )


def _tenant_module_response(tm) -> TenantModuleResponse:
    return TenantModuleResponse(
        id=tm.id,
        tenant_id=tm.tenant_id,
        module_id=tm.module_id,
        module_slug=tm.module.slug if tm.module else "",
        module_name=tm.module.name if tm.module else "",
        module_name_ru=tm.module.name_ru if tm.module else "",
        source=tm.source,
        enabled=tm.enabled,
        activated_at=tm.activated_at,
        expires_at=tm.expires_at,
    )


def _upgrade_request_response(req) -> UpgradeRequestResponse:
    return UpgradeRequestResponse(
        id=req.id,
        tenant_id=req.tenant_id,
        request_type=req.request_type,
        target_plan_id=req.target_plan_id,
        target_module_id=req.target_module_id,
        target_bundle_id=req.target_bundle_id,
        status=req.status,
        message=req.message,
        reviewed_by=req.reviewed_by,
        reviewed_at=req.reviewed_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
        target_plan_name=req.target_plan.name_ru if req.target_plan else None,
        target_module_name=req.target_module.name_ru if req.target_module else None,
        target_bundle_name=req.target_bundle.name_ru if req.target_bundle else None,
    )


# ============================================================================
# Public endpoints (no auth)
# ============================================================================


@router.get(
    "/public/plans",
    response_model=list[PlanResponse],
    summary="List all active plans with modules and limits",
)
async def list_plans_public(db: AsyncSession = Depends(get_db)):
    svc = PlanService(db)
    plans = await svc.list_plans(active_only=True)
    return [_plan_response(p) for p in plans]


@router.get(
    "/public/modules",
    response_model=list[BillingModuleResponse],
    summary="List all billing modules with prices",
)
async def list_modules_public(db: AsyncSession = Depends(get_db)):
    svc = PlanService(db)
    return await svc.list_modules()


@router.get(
    "/public/bundles",
    response_model=list[BundleResponse],
    summary="List all active bundles with modules",
)
async def list_bundles_public(db: AsyncSession = Depends(get_db)):
    svc = PlanService(db)
    bundles = await svc.list_bundles(active_only=True)
    return [_bundle_response(b) for b in bundles]


# ============================================================================
# Admin endpoints (tenant owner)
# ============================================================================


@router.get(
    "/admin/my-plan",
    response_model=MyPlanResponse,
    summary="Current tenant plan, modules, and usage",
    dependencies=[Depends(PermissionChecker("dashboard:read"))],
)
async def get_my_plan(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    plan_svc = PlanService(db)
    limit_svc = LimitService(db)

    from app.modules.tenants.models import Tenant
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = select(Tenant).options(selectinload(Tenant.plan)).where(Tenant.id == tenant_id)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    plan_resp = _plan_response(tenant.plan) if tenant and tenant.plan else None
    tenant_modules = await plan_svc.get_tenant_modules(tenant_id)
    usage_report = await limit_svc.get_full_usage_report(tenant_id)

    return MyPlanResponse(
        plan=plan_resp,
        modules=[_tenant_module_response(tm) for tm in tenant_modules],
        usage={k: UsageInfo(**v) for k, v in usage_report.items()},
    )


@router.get(
    "/admin/my-modules",
    response_model=MyModulesResponse,
    summary="List active modules for current tenant",
    dependencies=[Depends(PermissionChecker("dashboard:read"))],
)
async def get_my_modules(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    modules = await svc.get_tenant_modules(tenant_id)
    return MyModulesResponse(items=[_tenant_module_response(tm) for tm in modules])


@router.get(
    "/admin/my-limits",
    summary="Current resource usage vs plan limits",
    dependencies=[Depends(PermissionChecker("dashboard:read"))],
)
async def get_my_limits(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    svc = LimitService(db)
    return await svc.get_full_usage_report(tenant_id)


# ============================================================================
# Upgrade Requests (tenant owner)
# ============================================================================


@router.post(
    "/admin/upgrade-requests",
    response_model=UpgradeRequestResponse,
    summary="Create upgrade request",
    dependencies=[Depends(PermissionChecker("dashboard:read"))],
)
async def create_upgrade_request(
    data: UpgradeRequestCreate,
    token: TokenPayload = Depends(get_current_token),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    limiter = RateLimiter(redis)
    allowed, remaining, reset = await limiter.is_allowed(
        f"upgrade_req:{token.tenant_id}", max_requests=5, window_seconds=3600
    )
    if not allowed:
        raise RateLimitExceededError(
            message="Too many upgrade requests. Please wait before submitting another.",
            retry_after=reset,
        )

    svc = UpgradeRequestService(db)
    req = await svc.create_request(token.tenant_id, data.model_dump(exclude_none=True))

    # Best-effort notification to platform owner
    try:
        from app.modules.billing.notifications import notify_upgrade_request_created
        await notify_upgrade_request_created(db, token.tenant_id, data.request_type)
    except Exception:
        pass

    return _upgrade_request_response(req)


@router.get(
    "/admin/upgrade-requests",
    response_model=list[UpgradeRequestResponse],
    summary="List own upgrade requests",
    dependencies=[Depends(PermissionChecker("dashboard:read"))],
)
async def list_my_upgrade_requests(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    svc = UpgradeRequestService(db)
    requests = await svc.list_requests(tenant_id=tenant_id)
    return [_upgrade_request_response(r) for r in requests]


# ============================================================================
# Platform owner endpoints
# ============================================================================


@router.get(
    "/admin/platform/plans",
    response_model=list[PlanResponse],
    summary="List all plans (including inactive)",
)
async def list_plans_platform(
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    plans = await svc.list_plans(active_only=False)
    return [_plan_response(p) for p in plans]


@router.post(
    "/admin/platform/plans",
    response_model=PlanResponse,
    summary="Create plan",
)
async def create_plan(
    data: PlanCreate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    plan = await svc.create_plan(
        data.model_dump(exclude={"module_slugs"}),
        module_slugs=data.module_slugs or None,
    )
    return _plan_response(plan)


@router.patch(
    "/admin/platform/plans/{plan_id}",
    response_model=PlanResponse,
    summary="Update plan",
)
async def update_plan(
    plan_id: UUID,
    data: PlanUpdate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    plan = await svc.update_plan(
        plan_id,
        data.model_dump(exclude={"module_slugs"}, exclude_none=True),
        module_slugs=data.module_slugs,
    )
    return _plan_response(plan)


@router.get(
    "/admin/platform/modules",
    response_model=list[BillingModuleResponse],
    summary="List all billing modules",
)
async def list_modules_platform(
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    return await svc.list_modules()


@router.post(
    "/admin/platform/modules",
    response_model=BillingModuleResponse,
    summary="Create billing module",
)
async def create_module(
    data: BillingModuleCreate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    return await svc.create_module(data.model_dump())


@router.patch(
    "/admin/platform/modules/{module_id}",
    response_model=BillingModuleResponse,
    summary="Update billing module",
)
async def update_module(
    module_id: UUID,
    data: BillingModuleUpdate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    return await svc.update_module(module_id, data.model_dump(exclude_none=True))


@router.post(
    "/admin/platform/tenants/{tenant_id}/modules",
    response_model=TenantModuleResponse,
    summary="Add module to tenant",
)
async def add_tenant_module(
    tenant_id: UUID,
    data: TenantModuleCreate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    tm = await svc.add_tenant_module(tenant_id, data.module_slug, source=data.source)
    return _tenant_module_response(tm)


@router.delete(
    "/admin/platform/tenants/{tenant_id}/modules",
    summary="Remove module from tenant",
)
async def remove_tenant_module(
    tenant_id: UUID,
    data: TenantModuleRemove,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    await svc.remove_tenant_module(tenant_id, data.module_slug)
    return {"detail": "Module removed"}


# ── Platform: Upgrade Requests ──


@router.get(
    "/admin/platform/upgrade-requests",
    response_model=list[UpgradeRequestResponse],
    summary="List all upgrade requests (platform owner)",
)
async def list_upgrade_requests_platform(
    status: str | None = None,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = UpgradeRequestService(db)
    requests = await svc.list_requests(status=status)
    return [_upgrade_request_response(r) for r in requests]


@router.patch(
    "/admin/platform/upgrade-requests/{request_id}",
    response_model=UpgradeRequestResponse,
    summary="Approve or reject upgrade request",
)
async def review_upgrade_request(
    request_id: UUID,
    data: UpgradeRequestReview,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = UpgradeRequestService(db)
    if data.status == "approved":
        req = await svc.approve(request_id, user.id)
    else:
        req = await svc.reject(request_id, user.id)
    return _upgrade_request_response(req)


# ── Platform: Bundles ──


@router.get(
    "/admin/platform/bundles",
    response_model=list[BundleResponse],
    summary="List all bundles (including inactive)",
)
async def list_bundles_platform(
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    bundles = await svc.list_bundles(active_only=False)
    return [_bundle_response(b) for b in bundles]


@router.post(
    "/admin/platform/bundles",
    response_model=BundleResponse,
    summary="Create bundle",
)
async def create_bundle(
    data: BundleCreate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    bundle = await svc.create_bundle(
        data.model_dump(exclude={"module_slugs"}),
        module_slugs=data.module_slugs or None,
    )
    return _bundle_response(bundle)


@router.patch(
    "/admin/platform/bundles/{bundle_id}",
    response_model=BundleResponse,
    summary="Update bundle",
)
async def update_bundle(
    bundle_id: UUID,
    data: BundleUpdate,
    user: AdminUser = Depends(require_platform_owner),
    db: AsyncSession = Depends(get_db),
):
    svc = PlanService(db)
    bundle = await svc.update_bundle(
        bundle_id,
        data.model_dump(exclude={"module_slugs"}, exclude_none=True),
        module_slugs=data.module_slugs,
    )
    return _bundle_response(bundle)
