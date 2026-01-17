"""Dashboard module service layer."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, literal_column, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company.models import Employee, Service
from app.modules.content.models import Article, ArticleStatus, Case, FAQ, Review
from app.modules.dashboard.schemas import (
    ContentByStatus,
    ContentStatusBreakdown,
    ContentSummary,
    DashboardResponse,
    InquirySummary,
    RecentActivity,
)
from app.modules.leads.models import Inquiry, InquiryStatus


class DashboardService:
    """Service for dashboard statistics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_dashboard(self, tenant_id: UUID) -> DashboardResponse:
        """Get dashboard statistics for a tenant.
        
        Optimized to use minimal database queries:
        - Content summary: 1 query with UNION ALL
        - Inquiry summary: 1 query with conditional aggregation
        - Content by status: 1 query with GROUP BY
        
        Total: 3 queries instead of 14+
        """
        # Run all queries in parallel would require asyncio.gather,
        # but SQLAlchemy sessions aren't thread-safe.
        # Instead, we use optimized single queries for each section.
        
        summary = await self._get_content_summary_optimized(tenant_id)
        inquiries = await self._get_inquiry_summary_optimized(tenant_id)
        content_by_status = await self._get_content_by_status_optimized(tenant_id)

        # Recent activity (would need audit log - returning empty for now)
        recent_activity: list[RecentActivity] = []

        return DashboardResponse(
            summary=summary,
            inquiries=inquiries,
            content_by_status=content_by_status,
            recent_activity=recent_activity,
        )

    async def _get_content_summary_optimized(self, tenant_id: UUID) -> ContentSummary:
        """Get counts for all content types in a single query using UNION ALL."""
        # Build subqueries for each content type
        articles_q = (
            select(
                literal_column("'articles'").label("content_type"),
                func.count().label("cnt")
            )
            .select_from(Article)
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
        )
        
        cases_q = (
            select(
                literal_column("'cases'").label("content_type"),
                func.count().label("cnt")
            )
            .select_from(Case)
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
        )
        
        employees_q = (
            select(
                literal_column("'employees'").label("content_type"),
                func.count().label("cnt")
            )
            .select_from(Employee)
            .where(Employee.tenant_id == tenant_id)
            .where(Employee.deleted_at.is_(None))
        )
        
        services_q = (
            select(
                literal_column("'services'").label("content_type"),
                func.count().label("cnt")
            )
            .select_from(Service)
            .where(Service.tenant_id == tenant_id)
            .where(Service.deleted_at.is_(None))
        )
        
        faqs_q = (
            select(
                literal_column("'faqs'").label("content_type"),
                func.count().label("cnt")
            )
            .select_from(FAQ)
            .where(FAQ.tenant_id == tenant_id)
            .where(FAQ.deleted_at.is_(None))
        )
        
        reviews_q = (
            select(
                literal_column("'reviews'").label("content_type"),
                func.count().label("cnt")
            )
            .select_from(Review)
            .where(Review.tenant_id == tenant_id)
            .where(Review.deleted_at.is_(None))
        )
        
        # Combine all queries with UNION ALL
        combined = union_all(
            articles_q, cases_q, employees_q, services_q, faqs_q, reviews_q
        )
        
        result = await self.db.execute(combined)
        rows = result.all()
        
        # Convert to dict for easy lookup
        counts = {row.content_type: row.cnt for row in rows}
        
        return ContentSummary(
            total_articles=counts.get("articles", 0),
            total_cases=counts.get("cases", 0),
            total_team_members=counts.get("employees", 0),
            total_services=counts.get("services", 0),
            total_faqs=counts.get("faqs", 0),
            total_reviews=counts.get("reviews", 0),
        )

    async def _get_inquiry_summary_optimized(self, tenant_id: UUID) -> InquirySummary:
        """Get inquiry statistics in a single query using conditional aggregation."""
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        
        # Use conditional aggregation to get all counts in one query
        stmt = (
            select(
                func.count().label("total"),
                func.sum(
                    case(
                        (Inquiry.status == InquiryStatus.NEW.value, 1),
                        else_=0
                    )
                ).label("pending"),
                func.sum(
                    case(
                        (Inquiry.status == InquiryStatus.IN_PROGRESS.value, 1),
                        else_=0
                    )
                ).label("in_progress"),
                func.sum(
                    case(
                        (Inquiry.status == InquiryStatus.COMPLETED.value, 1),
                        else_=0
                    )
                ).label("done"),
                func.sum(
                    case(
                        (Inquiry.created_at >= month_start, 1),
                        else_=0
                    )
                ).label("this_month"),
            )
            .select_from(Inquiry)
            .where(Inquiry.tenant_id == tenant_id)
            .where(Inquiry.deleted_at.is_(None))
        )
        
        result = await self.db.execute(stmt)
        row = result.one()
        
        return InquirySummary(
            total=row.total or 0,
            pending=row.pending or 0,
            in_progress=row.in_progress or 0,
            done=row.done or 0,
            this_month=row.this_month or 0,
        )

    async def _get_content_by_status_optimized(self, tenant_id: UUID) -> ContentStatusBreakdown:
        """Get content breakdown by status using GROUP BY."""
        # Query for articles by status
        articles_stmt = (
            select(
                Article.status,
                func.count().label("cnt")
            )
            .where(Article.tenant_id == tenant_id)
            .where(Article.deleted_at.is_(None))
            .group_by(Article.status)
        )
        
        articles_result = await self.db.execute(articles_stmt)
        articles_counts = {row.status: row.cnt for row in articles_result.all()}
        
        # Query for cases by status
        cases_stmt = (
            select(
                Case.status,
                func.count().label("cnt")
            )
            .where(Case.tenant_id == tenant_id)
            .where(Case.deleted_at.is_(None))
            .group_by(Case.status)
        )
        
        cases_result = await self.db.execute(cases_stmt)
        cases_counts = {row.status: row.cnt for row in cases_result.all()}
        
        return ContentStatusBreakdown(
            articles=ContentByStatus(
                published=articles_counts.get(ArticleStatus.PUBLISHED.value, 0),
                draft=articles_counts.get(ArticleStatus.DRAFT.value, 0),
                archived=articles_counts.get(ArticleStatus.ARCHIVED.value, 0),
            ),
            cases=ContentByStatus(
                published=cases_counts.get(ArticleStatus.PUBLISHED.value, 0),
                draft=cases_counts.get(ArticleStatus.DRAFT.value, 0),
                archived=cases_counts.get(ArticleStatus.ARCHIVED.value, 0),
            ),
        )
