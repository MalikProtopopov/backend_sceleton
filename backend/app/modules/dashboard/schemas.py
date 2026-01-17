"""Pydantic schemas for dashboard module."""

from datetime import datetime

from pydantic import BaseModel


class ContentSummary(BaseModel):
    """Summary counts for content types."""

    total_articles: int = 0
    total_cases: int = 0
    total_team_members: int = 0
    total_services: int = 0
    total_faqs: int = 0
    total_reviews: int = 0


class InquirySummary(BaseModel):
    """Summary for inquiries."""

    total: int = 0
    pending: int = 0
    in_progress: int = 0
    done: int = 0
    this_month: int = 0


class ContentByStatus(BaseModel):
    """Content breakdown by status."""

    published: int = 0
    draft: int = 0
    archived: int = 0


class ContentStatusBreakdown(BaseModel):
    """Status breakdown for all content types."""

    articles: ContentByStatus = ContentByStatus()
    cases: ContentByStatus = ContentByStatus()


class RecentActivityUser(BaseModel):
    """User info in recent activity."""

    name: str
    email: str | None = None


class RecentActivityResource(BaseModel):
    """Resource info in recent activity."""

    type: str
    id: str
    title: str | None = None


class RecentActivity(BaseModel):
    """Recent activity item."""

    type: str
    action: str
    timestamp: datetime
    user: RecentActivityUser | None = None
    resource: RecentActivityResource | None = None


class DashboardResponse(BaseModel):
    """Dashboard API response."""

    summary: ContentSummary
    inquiries: InquirySummary
    content_by_status: ContentStatusBreakdown
    recent_activity: list[RecentActivity] = []

