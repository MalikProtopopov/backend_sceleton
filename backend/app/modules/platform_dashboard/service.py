"""Platform dashboard service layer.

Aggregates data across all tenants for the platform owner dashboard.
Every public method returns a Pydantic schema instance ready for the API response.
"""

from datetime import UTC, datetime, timedelta
from math import ceil
from uuid import UUID

from sqlalchemy import (
    case,
    cast,
    desc,
    extract,
    func,
    literal_column,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import AdminUser, AuditLog
from app.modules.company.models import Employee, Service
from app.modules.content.models import FAQ, Article, ArticleStatus, Case, Review, ReviewStatus
from app.modules.documents.models import Document
from app.modules.leads.models import Inquiry, InquiryStatus
from app.modules.platform_dashboard.schemas import (
    AlertSummary,
    AuditEntry,
    ContentBreakdown,
    ContentByStatus,
    FeatureFlagInfo,
    HealthAlert,
    InquiryBreakdown,
    PlatformAlerts,
    PlatformOverview,
    PlatformTrends,
    ReviewByStatus,
    TenantDetailStats,
    TenantRow,
    TenantTableResponse,
    TenantTrendSeries,
    TenantUserInfo,
    TrendPoint,
)
from app.modules.tenants.models import FeatureFlag, Tenant


class PlatformDashboardService:
    """Service for platform-wide dashboard statistics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ================================================================
    # 1. Overview
    # ================================================================

    async def get_overview(self) -> PlatformOverview:
        """Platform-level KPI cards.

        Executes 3 optimised queries:
        1. Tenant counts via conditional aggregation
        2. User counts via conditional aggregation
        3. Inquiry counts via conditional aggregation + inactive tenants
        """
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        if now.month == 1:
            prev_month_start = datetime(now.year - 1, 12, 1, tzinfo=UTC)
        else:
            prev_month_start = datetime(now.year, now.month - 1, 1, tzinfo=UTC)

        # -- Tenants -------------------------------------------------------
        tenant_stmt = select(
            func.count().label("total"),
            func.sum(case((Tenant.is_active.is_(True), 1), else_=0)).label("active"),
            func.sum(case((Tenant.is_active.is_(False), 1), else_=0)).label("inactive"),
        ).where(Tenant.deleted_at.is_(None))

        tenant_row = (await self.db.execute(tenant_stmt)).one()

        # -- Users ---------------------------------------------------------
        user_stmt = select(
            func.count().label("total"),
            func.sum(case((AdminUser.is_active.is_(True), 1), else_=0)).label("active"),
        ).where(AdminUser.deleted_at.is_(None))

        user_row = (await self.db.execute(user_stmt)).one()

        # -- Inquiries + inactive tenants ----------------------------------
        inq_stmt = select(
            func.count().label("total"),
            func.sum(case((Inquiry.created_at >= month_start, 1), else_=0)).label(
                "this_month"
            ),
            func.sum(
                case(
                    (
                        (Inquiry.created_at >= prev_month_start)
                        & (Inquiry.created_at < month_start),
                        1,
                    ),
                    else_=0,
                )
            ).label("prev_month"),
        ).where(Inquiry.deleted_at.is_(None))

        inq_row = (await self.db.execute(inq_stmt)).one()

        # Inactive tenants (no login in last 30 days among active tenants)
        cutoff = now - timedelta(days=30)
        last_login_sub = (
            select(
                AdminUser.tenant_id,
                func.max(AdminUser.last_login_at).label("latest"),
            )
            .where(AdminUser.deleted_at.is_(None))
            .group_by(AdminUser.tenant_id)
            .subquery()
        )
        inactive_stmt = (
            select(func.count())
            .select_from(Tenant)
            .outerjoin(last_login_sub, Tenant.id == last_login_sub.c.tenant_id)
            .where(Tenant.deleted_at.is_(None))
            .where(Tenant.is_active.is_(True))
            .where(
                (last_login_sub.c.latest < cutoff) | (last_login_sub.c.latest.is_(None))
            )
        )
        inactive_30d = (await self.db.execute(inactive_stmt)).scalar() or 0

        return PlatformOverview(
            total_tenants=tenant_row.total or 0,
            active_tenants=tenant_row.active or 0,
            inactive_tenants=tenant_row.inactive or 0,
            total_users=user_row.total or 0,
            active_users=user_row.active or 0,
            total_inquiries=inq_row.total or 0,
            inquiries_this_month=inq_row.this_month or 0,
            inquiries_prev_month=inq_row.prev_month or 0,
            inactive_tenants_30d=inactive_30d,
        )

    # ================================================================
    # 2. Tenants Table
    # ================================================================

    async def get_tenants_table(
        self,
        page: int = 1,
        per_page: int = 25,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        search: str | None = None,
    ) -> TenantTableResponse:
        """Paginated tenant list with aggregated metrics per tenant."""
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)

        # --- sub: users ---------------------------------------------------
        users_sub = (
            select(
                AdminUser.tenant_id,
                func.count().label("users_count"),
                func.sum(case((AdminUser.is_active.is_(True), 1), else_=0)).label(
                    "active_users_count"
                ),
                func.max(AdminUser.last_login_at).label("last_login_at"),
            )
            .where(AdminUser.deleted_at.is_(None))
            .group_by(AdminUser.tenant_id)
            .subquery("users_sub")
        )

        # --- sub: published content counts --------------------------------
        # Articles (status = 'published')
        art_sub = (
            select(
                Article.tenant_id,
                func.count().label("articles_count"),
            )
            .where(Article.deleted_at.is_(None))
            .where(Article.status == ArticleStatus.PUBLISHED.value)
            .group_by(Article.tenant_id)
            .subquery("art_sub")
        )
        # Cases
        case_sub = (
            select(
                Case.tenant_id,
                func.count().label("cases_count"),
            )
            .where(Case.deleted_at.is_(None))
            .where(Case.status == ArticleStatus.PUBLISHED.value)
            .group_by(Case.tenant_id)
            .subquery("case_sub")
        )
        # Services (is_published = True)
        svc_sub = (
            select(
                Service.tenant_id,
                func.count().label("services_count"),
            )
            .where(Service.deleted_at.is_(None))
            .where(Service.is_published.is_(True))
            .group_by(Service.tenant_id)
            .subquery("svc_sub")
        )

        # --- sub: inquiries -----------------------------------------------
        inq_sub = (
            select(
                Inquiry.tenant_id,
                func.count().label("inquiries_total"),
                func.sum(
                    case((Inquiry.created_at >= month_start, 1), else_=0)
                ).label("inquiries_this_month"),
                func.sum(
                    case((Inquiry.status == InquiryStatus.NEW.value, 1), else_=0)
                ).label("inquiries_new"),
            )
            .where(Inquiry.deleted_at.is_(None))
            .group_by(Inquiry.tenant_id)
            .subquery("inq_sub")
        )

        # --- sub: feature flags -------------------------------------------
        ff_sub = (
            select(
                FeatureFlag.tenant_id,
                func.count().label("enabled_features_count"),
                func.array_agg(FeatureFlag.feature_name).label("enabled_features"),
            )
            .where(FeatureFlag.enabled.is_(True))
            .group_by(FeatureFlag.tenant_id)
            .subquery("ff_sub")
        )

        # --- main query ---------------------------------------------------
        base = (
            select(
                Tenant.id,
                Tenant.name,
                Tenant.slug,
                Tenant.domain,
                Tenant.is_active,
                Tenant.created_at,
                func.coalesce(users_sub.c.users_count, 0).label("users_count"),
                func.coalesce(users_sub.c.active_users_count, 0).label("active_users_count"),
                func.coalesce(art_sub.c.articles_count, 0).label("articles_count"),
                func.coalesce(case_sub.c.cases_count, 0).label("cases_count"),
                func.coalesce(svc_sub.c.services_count, 0).label("services_count"),
                (
                    func.coalesce(art_sub.c.articles_count, 0)
                    + func.coalesce(case_sub.c.cases_count, 0)
                    + func.coalesce(svc_sub.c.services_count, 0)
                ).label("content_count"),
                func.coalesce(inq_sub.c.inquiries_total, 0).label("inquiries_total"),
                func.coalesce(inq_sub.c.inquiries_this_month, 0).label(
                    "inquiries_this_month"
                ),
                func.coalesce(inq_sub.c.inquiries_new, 0).label("inquiries_new"),
                users_sub.c.last_login_at.label("last_login_at"),
                func.coalesce(ff_sub.c.enabled_features_count, 0).label(
                    "enabled_features_count"
                ),
                func.coalesce(
                    ff_sub.c.enabled_features,
                    cast(literal_column("'{}'"), type_=ff_sub.c.enabled_features.type),
                ).label("enabled_features"),
            )
            .select_from(Tenant)
            .outerjoin(users_sub, Tenant.id == users_sub.c.tenant_id)
            .outerjoin(art_sub, Tenant.id == art_sub.c.tenant_id)
            .outerjoin(case_sub, Tenant.id == case_sub.c.tenant_id)
            .outerjoin(svc_sub, Tenant.id == svc_sub.c.tenant_id)
            .outerjoin(inq_sub, Tenant.id == inq_sub.c.tenant_id)
            .outerjoin(ff_sub, Tenant.id == ff_sub.c.tenant_id)
            .where(Tenant.deleted_at.is_(None))
        )

        # Optional text search
        if search:
            like = f"%{search}%"
            base = base.where(
                Tenant.name.ilike(like)
                | Tenant.slug.ilike(like)
                | Tenant.domain.ilike(like)
            )

        # Count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        # Sorting — map allowed column names to actual columns
        sort_map = {
            "name": Tenant.name,
            "slug": Tenant.slug,
            "created_at": Tenant.created_at,
            "is_active": Tenant.is_active,
            "users_count": literal_column("users_count"),
            "content_count": literal_column("content_count"),
            "inquiries_total": literal_column("inquiries_total"),
            "inquiries_this_month": literal_column("inquiries_this_month"),
            "last_login_at": literal_column("last_login_at"),
            "enabled_features_count": literal_column("enabled_features_count"),
        }
        order_col = sort_map.get(sort_by, Tenant.created_at)
        if sort_dir == "asc":
            base = base.order_by(order_col)
        else:
            base = base.order_by(desc(order_col))

        # Pagination
        offset = (page - 1) * per_page
        base = base.offset(offset).limit(per_page)

        result = await self.db.execute(base)
        rows = result.all()

        items = [
            TenantRow(
                id=r.id,
                name=r.name,
                slug=r.slug,
                domain=r.domain,
                is_active=r.is_active,
                created_at=r.created_at,
                users_count=r.users_count,
                active_users_count=r.active_users_count,
                articles_count=r.articles_count,
                cases_count=r.cases_count,
                services_count=r.services_count,
                content_count=r.content_count,
                inquiries_total=r.inquiries_total,
                inquiries_this_month=r.inquiries_this_month,
                inquiries_new=r.inquiries_new,
                last_login_at=r.last_login_at,
                enabled_features_count=r.enabled_features_count,
                enabled_features=r.enabled_features or [],
            )
            for r in rows
        ]

        return TenantTableResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            pages=ceil(total / per_page) if per_page else 0,
        )

    # ================================================================
    # 3. Tenant Detail (drill-down)
    # ================================================================

    async def get_tenant_details(self, tenant_id: UUID) -> TenantDetailStats:
        """Full statistics for a single tenant."""
        from app.core.exceptions import NotFoundError

        # Verify tenant exists
        tenant_stmt = select(Tenant).where(
            Tenant.id == tenant_id, Tenant.deleted_at.is_(None)
        )
        tenant = (await self.db.execute(tenant_stmt)).scalar_one_or_none()
        if not tenant:
            raise NotFoundError("Tenant", tenant_id)

        content = await self._content_breakdown(tenant_id)
        inquiries = await self._inquiry_breakdown(tenant_id)
        flags = await self._feature_flags(tenant_id)
        users = await self._tenant_users(tenant_id)
        activity = await self._recent_audit(tenant_id)

        return TenantDetailStats(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            is_active=tenant.is_active,
            content=content,
            inquiries=inquiries,
            feature_flags=flags,
            users=users,
            recent_activity=activity,
        )

    # --- detail helpers ---

    async def _content_breakdown(self, tenant_id: UUID) -> ContentBreakdown:
        """Count content items by type and status for a tenant."""
        # Articles / Cases / Documents: status enum (draft/published/archived)
        articles_stmt = (
            select(Article.status, func.count().label("cnt"))
            .where(Article.tenant_id == tenant_id, Article.deleted_at.is_(None))
            .group_by(Article.status)
        )
        cases_stmt = (
            select(Case.status, func.count().label("cnt"))
            .where(Case.tenant_id == tenant_id, Case.deleted_at.is_(None))
            .group_by(Case.status)
        )
        docs_stmt = (
            select(Document.status, func.count().label("cnt"))
            .where(Document.tenant_id == tenant_id, Document.deleted_at.is_(None))
            .group_by(Document.status)
        )

        art_rows = (await self.db.execute(articles_stmt)).all()
        case_rows = (await self.db.execute(cases_stmt)).all()
        doc_rows = (await self.db.execute(docs_stmt)).all()

        def _to_cbs(rows: list) -> ContentByStatus:
            m = {r.status: r.cnt for r in rows}
            return ContentByStatus(
                published=m.get("published", 0),
                draft=m.get("draft", 0),
                archived=m.get("archived", 0),
            )

        # Services / Employees: is_published boolean
        svc_stmt = (
            select(
                func.count().label("total"),
                func.sum(case((Service.is_published.is_(True), 1), else_=0)).label("pub"),
            )
            .where(Service.tenant_id == tenant_id, Service.deleted_at.is_(None))
        )
        emp_stmt = (
            select(
                func.count().label("total"),
                func.sum(case((Employee.is_published.is_(True), 1), else_=0)).label("pub"),
            )
            .where(Employee.tenant_id == tenant_id, Employee.deleted_at.is_(None))
        )

        # FAQs: is_published boolean (no PublishableMixin, direct field)
        faq_stmt = (
            select(
                func.count().label("total"),
                func.sum(case((FAQ.is_published.is_(True), 1), else_=0)).label("pub"),
            )
            .where(FAQ.tenant_id == tenant_id, FAQ.deleted_at.is_(None))
        )

        # Reviews: status enum (pending/approved/rejected)
        rev_stmt = (
            select(Review.status, func.count().label("cnt"))
            .where(Review.tenant_id == tenant_id, Review.deleted_at.is_(None))
            .group_by(Review.status)
        )

        svc_row = (await self.db.execute(svc_stmt)).one()
        emp_row = (await self.db.execute(emp_stmt)).one()
        faq_row = (await self.db.execute(faq_stmt)).one()
        rev_rows = (await self.db.execute(rev_stmt)).all()

        rev_map = {r.status: r.cnt for r in rev_rows}

        return ContentBreakdown(
            articles=_to_cbs(art_rows),
            cases=_to_cbs(case_rows),
            documents=_to_cbs(doc_rows),
            services=svc_row.pub or 0,
            services_total=svc_row.total or 0,
            employees=emp_row.pub or 0,
            employees_total=emp_row.total or 0,
            faqs=faq_row.pub or 0,
            faqs_total=faq_row.total or 0,
            reviews=ReviewByStatus(
                pending=rev_map.get(ReviewStatus.PENDING.value, 0),
                approved=rev_map.get(ReviewStatus.APPROVED.value, 0),
                rejected=rev_map.get(ReviewStatus.REJECTED.value, 0),
            ),
        )

    async def _inquiry_breakdown(self, tenant_id: UUID) -> InquiryBreakdown:
        """Inquiry analytics for a tenant."""
        base_where = [Inquiry.tenant_id == tenant_id, Inquiry.deleted_at.is_(None)]

        # Total
        total = (
            await self.db.execute(
                select(func.count()).where(*base_where)
            )
        ).scalar() or 0

        # By status
        status_stmt = (
            select(Inquiry.status, func.count().label("cnt"))
            .where(*base_where)
            .group_by(Inquiry.status)
        )
        by_status = {r.status: r.cnt for r in (await self.db.execute(status_stmt)).all()}

        # By UTM source
        utm_stmt = (
            select(Inquiry.utm_source, func.count().label("cnt"))
            .where(*base_where)
            .where(Inquiry.utm_source.isnot(None))
            .group_by(Inquiry.utm_source)
            .order_by(desc("cnt"))
            .limit(20)
        )
        by_utm = {r.utm_source: r.cnt for r in (await self.db.execute(utm_stmt)).all()}

        # By device type
        dev_stmt = (
            select(Inquiry.device_type, func.count().label("cnt"))
            .where(*base_where)
            .where(Inquiry.device_type.isnot(None))
            .group_by(Inquiry.device_type)
        )
        by_device = {r.device_type: r.cnt for r in (await self.db.execute(dev_stmt)).all()}

        # By country top-10
        geo_stmt = (
            select(Inquiry.country, func.count().label("cnt"))
            .where(*base_where)
            .where(Inquiry.country.isnot(None))
            .group_by(Inquiry.country)
            .order_by(desc("cnt"))
            .limit(10)
        )
        geo_rows = (await self.db.execute(geo_stmt)).all()
        by_country = [{"country": r.country, "count": r.cnt} for r in geo_rows]

        # Top pages
        pages_stmt = (
            select(Inquiry.page_path, func.count().label("cnt"))
            .where(*base_where)
            .where(Inquiry.page_path.isnot(None))
            .group_by(Inquiry.page_path)
            .order_by(desc("cnt"))
            .limit(10)
        )
        page_rows = (await self.db.execute(pages_stmt)).all()
        top_pages = [{"page": r.page_path, "count": r.cnt} for r in page_rows]

        # Average processing time (created_at -> contacted_at) in hours
        avg_stmt = (
            select(
                func.avg(
                    extract("epoch", Inquiry.contacted_at - Inquiry.created_at) / 3600.0
                ).label("avg_hours")
            )
            .where(*base_where)
            .where(Inquiry.contacted_at.isnot(None))
        )
        avg_hours = (await self.db.execute(avg_stmt)).scalar()

        return InquiryBreakdown(
            total=total,
            by_status=by_status,
            by_utm_source=by_utm,
            by_device_type=by_device,
            by_country_top10=by_country,
            top_pages=top_pages,
            avg_processing_hours=round(avg_hours, 1) if avg_hours is not None else None,
        )

    async def _feature_flags(self, tenant_id: UUID) -> list[FeatureFlagInfo]:
        stmt = (
            select(FeatureFlag.feature_name, FeatureFlag.enabled)
            .where(FeatureFlag.tenant_id == tenant_id)
            .order_by(FeatureFlag.feature_name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [FeatureFlagInfo(feature_name=r.feature_name, enabled=r.enabled) for r in rows]

    async def _tenant_users(self, tenant_id: UUID) -> list[TenantUserInfo]:
        from app.modules.auth.models import Role

        stmt = (
            select(
                AdminUser.id,
                AdminUser.email,
                AdminUser.first_name,
                AdminUser.last_name,
                AdminUser.is_active,
                Role.name.label("role_name"),
                AdminUser.last_login_at,
            )
            .outerjoin(Role, AdminUser.role_id == Role.id)
            .where(AdminUser.tenant_id == tenant_id, AdminUser.deleted_at.is_(None))
            .order_by(AdminUser.first_name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            TenantUserInfo(
                id=r.id,
                email=r.email,
                first_name=r.first_name,
                last_name=r.last_name,
                is_active=r.is_active,
                role_name=r.role_name,
                last_login_at=r.last_login_at,
            )
            for r in rows
        ]

    async def _recent_audit(self, tenant_id: UUID, limit: int = 20) -> list[AuditEntry]:
        stmt = (
            select(
                AuditLog.id,
                AuditLog.action,
                AuditLog.resource_type,
                AuditLog.resource_id,
                AdminUser.email.label("user_email"),
                AuditLog.created_at,
            )
            .outerjoin(AdminUser, AuditLog.user_id == AdminUser.id)
            .where(AuditLog.tenant_id == tenant_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            AuditEntry(
                id=r.id,
                action=r.action,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                user_email=r.user_email,
                created_at=r.created_at,
            )
            for r in rows
        ]

    # ================================================================
    # 4. Trends (time-series)
    # ================================================================

    async def get_trends(self, days: int = 90) -> PlatformTrends:
        """Time-series data for platform graphs."""
        now = datetime.now(UTC)
        start = now - timedelta(days=days)

        new_tenants = await self._trend_by_month(
            Tenant, Tenant.created_at, start
        )
        new_users = await self._trend_by_month(
            AdminUser, AdminUser.created_at, start, soft_delete=True
        )
        inquiries = await self._trend_by_day(
            Inquiry, Inquiry.created_at, start, soft_delete=True
        )
        logins = await self._logins_by_day(start)
        inq_by_tenant = await self._inquiries_by_tenant(start)

        return PlatformTrends(
            new_tenants_by_month=new_tenants,
            new_users_by_month=new_users,
            inquiries_by_day=inquiries,
            logins_by_day=logins,
            inquiries_by_tenant=inq_by_tenant,
        )

    async def _trend_by_month(
        self,
        model: type,
        date_col,
        start: datetime,
        *,
        soft_delete: bool = False,
    ) -> list[TrendPoint]:
        stmt = (
            select(
                func.to_char(func.date_trunc("month", date_col), "YYYY-MM").label("d"),
                func.count().label("v"),
            )
            .where(date_col >= start)
        )
        if soft_delete and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))
        stmt = stmt.group_by("d").order_by("d")
        rows = (await self.db.execute(stmt)).all()
        return [TrendPoint(date=r.d, value=r.v) for r in rows]

    async def _trend_by_day(
        self,
        model: type,
        date_col,
        start: datetime,
        *,
        soft_delete: bool = False,
    ) -> list[TrendPoint]:
        stmt = (
            select(
                func.to_char(func.date_trunc("day", date_col), "YYYY-MM-DD").label("d"),
                func.count().label("v"),
            )
            .where(date_col >= start)
        )
        if soft_delete and hasattr(model, "deleted_at"):
            stmt = stmt.where(model.deleted_at.is_(None))
        stmt = stmt.group_by("d").order_by("d")
        rows = (await self.db.execute(stmt)).all()
        return [TrendPoint(date=r.d, value=r.v) for r in rows]

    async def _logins_by_day(self, start: datetime) -> list[TrendPoint]:
        stmt = (
            select(
                func.to_char(func.date_trunc("day", AuditLog.created_at), "YYYY-MM-DD").label("d"),
                func.count().label("v"),
            )
            .where(AuditLog.created_at >= start)
            .where(AuditLog.action == "login")
            .group_by("d")
            .order_by("d")
        )
        rows = (await self.db.execute(stmt)).all()
        return [TrendPoint(date=r.d, value=r.v) for r in rows]

    async def _inquiries_by_tenant(
        self, start: datetime, top_n: int = 10
    ) -> list[TenantTrendSeries]:
        """Top N tenants by inquiry volume with daily breakdown."""
        # Find top tenants
        top_stmt = (
            select(Inquiry.tenant_id, func.count().label("cnt"))
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.created_at >= start)
            .group_by(Inquiry.tenant_id)
            .order_by(desc("cnt"))
            .limit(top_n)
        )
        top_rows = (await self.db.execute(top_stmt)).all()
        if not top_rows:
            return []

        tenant_ids = [r.tenant_id for r in top_rows]

        # Fetch tenant names
        names_stmt = select(Tenant.id, Tenant.name).where(Tenant.id.in_(tenant_ids))
        names = {r.id: r.name for r in (await self.db.execute(names_stmt)).all()}

        # Daily data per tenant
        daily_stmt = (
            select(
                Inquiry.tenant_id,
                func.to_char(
                    func.date_trunc("day", Inquiry.created_at), "YYYY-MM-DD"
                ).label("d"),
                func.count().label("v"),
            )
            .where(Inquiry.tenant_id.in_(tenant_ids))
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.created_at >= start)
            .group_by(Inquiry.tenant_id, "d")
            .order_by(Inquiry.tenant_id, "d")
        )
        daily_rows = (await self.db.execute(daily_stmt)).all()

        # Group by tenant
        from collections import defaultdict

        groups: dict[UUID, list[TrendPoint]] = defaultdict(list)
        for r in daily_rows:
            groups[r.tenant_id].append(TrendPoint(date=r.d, value=r.v))

        return [
            TenantTrendSeries(
                tenant_id=tid,
                tenant_name=names.get(tid, "Unknown"),
                data=groups.get(tid, []),
            )
            for tid in tenant_ids
        ]

    # ================================================================
    # 5. Health Alerts
    # ================================================================

    async def get_health_alerts(self) -> PlatformAlerts:
        """Detect health issues across tenants."""
        alerts: list[HealthAlert] = []

        await self._alert_inactive_tenants(alerts)
        await self._alert_stale_inquiries(alerts)
        await self._alert_empty_tenants(alerts)
        await self._alert_low_features(alerts)
        await self._alert_spam_ratio(alerts)
        await self._alert_declining_inquiries(alerts)

        summary = AlertSummary(
            critical=sum(1 for a in alerts if a.severity == "critical"),
            warning=sum(1 for a in alerts if a.severity == "warning"),
            info=sum(1 for a in alerts if a.severity == "info"),
        )
        return PlatformAlerts(alerts=alerts, summary=summary)

    async def _alert_inactive_tenants(self, alerts: list[HealthAlert]) -> None:
        """Tenants with no login in last 14 days."""
        cutoff = datetime.now(UTC) - timedelta(days=14)
        last_login_sub = (
            select(
                AdminUser.tenant_id,
                func.max(AdminUser.last_login_at).label("latest"),
            )
            .where(AdminUser.deleted_at.is_(None))
            .group_by(AdminUser.tenant_id)
            .subquery()
        )
        stmt = (
            select(Tenant.id, Tenant.name, last_login_sub.c.latest)
            .outerjoin(last_login_sub, Tenant.id == last_login_sub.c.tenant_id)
            .where(Tenant.deleted_at.is_(None))
            .where(Tenant.is_active.is_(True))
            .where(
                (last_login_sub.c.latest < cutoff) | (last_login_sub.c.latest.is_(None))
            )
        )
        for r in (await self.db.execute(stmt)).all():
            alerts.append(
                HealthAlert(
                    type="inactive_tenant",
                    severity="warning",
                    tenant_id=r.id,
                    tenant_name=r.name,
                    message="No user login for >14 days",
                    details={"last_login": r.latest.isoformat() if r.latest else None},
                )
            )

    async def _alert_stale_inquiries(self, alerts: list[HealthAlert]) -> None:
        """Tenants with unprocessed inquiries older than 3 days."""
        cutoff = datetime.now(UTC) - timedelta(days=3)
        stmt = (
            select(
                Inquiry.tenant_id,
                Tenant.name,
                func.count().label("stale_count"),
            )
            .join(Tenant, Inquiry.tenant_id == Tenant.id)
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.status == InquiryStatus.NEW.value)
            .where(Inquiry.created_at < cutoff)
            .group_by(Inquiry.tenant_id, Tenant.name)
        )
        for r in (await self.db.execute(stmt)).all():
            alerts.append(
                HealthAlert(
                    type="stale_inquiries",
                    severity="critical",
                    tenant_id=r.tenant_id,
                    tenant_name=r.name,
                    message=f"{r.stale_count} unprocessed inquiries older than 3 days",
                    details={"count": r.stale_count},
                )
            )

    async def _alert_empty_tenants(self, alerts: list[HealthAlert]) -> None:
        """Active tenants with zero published content."""
        # Count published articles + cases + services per tenant
        art = (
            select(Article.tenant_id, func.count().label("c"))
            .where(Article.deleted_at.is_(None))
            .where(Article.status == ArticleStatus.PUBLISHED.value)
            .group_by(Article.tenant_id)
            .subquery()
        )
        cas = (
            select(Case.tenant_id, func.count().label("c"))
            .where(Case.deleted_at.is_(None))
            .where(Case.status == ArticleStatus.PUBLISHED.value)
            .group_by(Case.tenant_id)
            .subquery()
        )
        svc = (
            select(Service.tenant_id, func.count().label("c"))
            .where(Service.deleted_at.is_(None))
            .where(Service.is_published.is_(True))
            .group_by(Service.tenant_id)
            .subquery()
        )

        stmt = (
            select(Tenant.id, Tenant.name)
            .outerjoin(art, Tenant.id == art.c.tenant_id)
            .outerjoin(cas, Tenant.id == cas.c.tenant_id)
            .outerjoin(svc, Tenant.id == svc.c.tenant_id)
            .where(Tenant.deleted_at.is_(None))
            .where(Tenant.is_active.is_(True))
            .where(
                (func.coalesce(art.c.c, 0) + func.coalesce(cas.c.c, 0) + func.coalesce(svc.c.c, 0))
                == 0
            )
        )
        for r in (await self.db.execute(stmt)).all():
            alerts.append(
                HealthAlert(
                    type="empty_tenant",
                    severity="info",
                    tenant_id=r.id,
                    tenant_name=r.name,
                    message="No published content (articles, cases, or services)",
                )
            )

    async def _alert_low_features(self, alerts: list[HealthAlert]) -> None:
        """Active tenants with fewer than 3 enabled features."""
        ff_sub = (
            select(
                FeatureFlag.tenant_id,
                func.count().label("cnt"),
            )
            .where(FeatureFlag.enabled.is_(True))
            .group_by(FeatureFlag.tenant_id)
            .subquery()
        )
        stmt = (
            select(Tenant.id, Tenant.name, func.coalesce(ff_sub.c.cnt, 0).label("cnt"))
            .outerjoin(ff_sub, Tenant.id == ff_sub.c.tenant_id)
            .where(Tenant.deleted_at.is_(None))
            .where(Tenant.is_active.is_(True))
            .where(func.coalesce(ff_sub.c.cnt, 0) < 3)
        )
        for r in (await self.db.execute(stmt)).all():
            alerts.append(
                HealthAlert(
                    type="low_feature_adoption",
                    severity="info",
                    tenant_id=r.id,
                    tenant_name=r.name,
                    message=f"Only {r.cnt} features enabled (upsell opportunity)",
                    details={"enabled_count": r.cnt},
                )
            )

    async def _alert_spam_ratio(self, alerts: list[HealthAlert]) -> None:
        """Tenants where >50% of inquiries are spam."""
        stmt = (
            select(
                Inquiry.tenant_id,
                Tenant.name,
                func.count().label("total"),
                func.sum(
                    case((Inquiry.status == InquiryStatus.SPAM.value, 1), else_=0)
                ).label("spam"),
            )
            .join(Tenant, Inquiry.tenant_id == Tenant.id)
            .where(Inquiry.deleted_at.is_(None))
            .group_by(Inquiry.tenant_id, Tenant.name)
            .having(func.count() >= 5)  # at least 5 inquiries to be relevant
        )
        for r in (await self.db.execute(stmt)).all():
            spam_count = r.spam or 0
            if r.total > 0 and (spam_count / r.total) > 0.5:
                alerts.append(
                    HealthAlert(
                        type="high_spam_ratio",
                        severity="warning",
                        tenant_id=r.tenant_id,
                        tenant_name=r.name,
                        message=f"{spam_count}/{r.total} inquiries marked as spam ({round(spam_count / r.total * 100)}%)",
                        details={"spam": spam_count, "total": r.total},
                    )
                )

    async def _alert_declining_inquiries(self, alerts: list[HealthAlert]) -> None:
        """Tenants where this month's inquiries dropped >50% vs previous month."""
        now = datetime.now(UTC)
        month_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        if now.month == 1:
            prev_start = datetime(now.year - 1, 12, 1, tzinfo=UTC)
        else:
            prev_start = datetime(now.year, now.month - 1, 1, tzinfo=UTC)

        stmt = (
            select(
                Inquiry.tenant_id,
                Tenant.name,
                func.sum(
                    case((Inquiry.created_at >= month_start, 1), else_=0)
                ).label("cur"),
                func.sum(
                    case(
                        (
                            (Inquiry.created_at >= prev_start)
                            & (Inquiry.created_at < month_start),
                            1,
                        ),
                        else_=0,
                    )
                ).label("prev"),
            )
            .join(Tenant, Inquiry.tenant_id == Tenant.id)
            .where(Inquiry.deleted_at.is_(None))
            .where(Inquiry.created_at >= prev_start)
            .group_by(Inquiry.tenant_id, Tenant.name)
        )
        for r in (await self.db.execute(stmt)).all():
            prev_count = r.prev or 0
            cur_count = r.cur or 0
            if prev_count >= 5 and cur_count < (prev_count * 0.5):
                drop_pct = round((1 - cur_count / prev_count) * 100)
                alerts.append(
                    HealthAlert(
                        type="declining_inquiries",
                        severity="warning",
                        tenant_id=r.tenant_id,
                        tenant_name=r.name,
                        message=f"Inquiries dropped {drop_pct}% vs previous month ({cur_count} vs {prev_count})",
                        details={"current": cur_count, "previous": prev_count},
                    )
                )
