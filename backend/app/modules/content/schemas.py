"""Pydantic schemas for content module."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.company.schemas import ServiceResponse


class ArticleStatus(str, Enum):
    """Article publication status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ============================================================================
# Topic Schemas
# ============================================================================


class TopicLocaleBase(BaseModel):
    """Base schema for topic locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class TopicLocaleCreate(TopicLocaleBase):
    """Schema for creating topic locale."""

    pass


class TopicLocaleUpdate(BaseModel):
    """Schema for updating topic locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class TopicLocaleResponse(TopicLocaleBase):
    """Schema for topic locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    topic_id: UUID
    created_at: datetime
    updated_at: datetime


class TopicBase(BaseModel):
    """Base schema for topic."""

    icon: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=7)
    sort_order: int = 0


class TopicCreate(TopicBase):
    """Schema for creating a topic."""

    locales: list[TopicLocaleCreate] = Field(..., min_length=1)


class TopicUpdate(BaseModel):
    """Schema for updating a topic."""

    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class TopicResponse(TopicBase):
    """Schema for topic response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    locales: list[TopicLocaleResponse] = []


class TopicPublicResponse(BaseModel):
    """Schema for public topic response."""

    id: UUID
    slug: str
    title: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None


class TopicWithArticlesCountPublicResponse(BaseModel):
    """Schema for public topic response with article count."""

    id: UUID
    slug: str
    title: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    articles_count: int = Field(default=0, description="Number of published articles in this topic")


class TopicDetailPublicResponse(BaseModel):
    """Schema for public topic detail response with SEO fields and article count."""

    id: UUID
    slug: str
    title: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    meta_keywords: str | None = None
    og_image: str | None = None
    articles_count: int = 0


# ============================================================================
# Article Schemas
# ============================================================================


class ArticleLocaleBase(BaseModel):
    """Base schema for article locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    excerpt: str | None = Field(default=None, max_length=500)
    content: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class ArticleLocaleCreate(ArticleLocaleBase):
    """Schema for creating article locale."""

    pass


class ArticleLocaleUpdate(BaseModel):
    """Schema for updating article locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    excerpt: str | None = Field(default=None, max_length=500)
    content: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class ArticleLocaleResponse(ArticleLocaleBase):
    """Schema for article locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    article_id: UUID
    created_at: datetime
    updated_at: datetime


class ArticleBase(BaseModel):
    """Base schema for article."""

    status: ArticleStatus = ArticleStatus.DRAFT
    reading_time_minutes: int | None = None
    sort_order: int = 0


class ArticleCreate(ArticleBase):
    """Schema for creating an article.
    
    Note: cover_image_url is managed via POST /admin/articles/{id}/cover-image endpoint.
    """

    locales: list[ArticleLocaleCreate] = Field(..., min_length=1)
    topic_ids: list[UUID] = Field(default_factory=list)


class ArticleUpdate(BaseModel):
    """Schema for updating an article.
    
    Note: cover_image_url is managed via POST/DELETE /admin/articles/{id}/cover-image endpoints.
    """

    status: ArticleStatus | None = None
    reading_time_minutes: int | None = None
    sort_order: int | None = None
    topic_ids: list[UUID] | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class ArticleResponse(ArticleBase):
    """Schema for article response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    cover_image_url: str | None = None
    version: int
    published_at: datetime | None = None
    view_count: int = 0
    author_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    locales: list[ArticleLocaleResponse] = []
    topics: list["ArticleTopicResponse"] = []


class ArticleTopicResponse(BaseModel):
    """Schema for article topic in response."""

    model_config = ConfigDict(from_attributes=True)

    topic_id: UUID


class ArticlePublicResponse(BaseModel):
    """Schema for public article response."""

    id: UUID
    slug: str
    title: str
    excerpt: str | None = None
    content: str | None = None
    cover_image_url: str | None = None
    reading_time_minutes: int | None = None
    published_at: datetime | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    topics: list[TopicPublicResponse] = []


class ArticleListResponse(BaseModel):
    """Schema for article list response."""

    items: list[ArticleResponse]
    total: int
    page: int
    page_size: int


class ArticlePublicListResponse(BaseModel):
    """Schema for public article list response."""

    items: list[ArticlePublicResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# FAQ Schemas
# ============================================================================


class FAQLocaleBase(BaseModel):
    """Base schema for FAQ locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    question: str = Field(..., min_length=5, max_length=500)
    answer: str = Field(..., min_length=1)


class FAQLocaleCreate(FAQLocaleBase):
    """Schema for creating FAQ locale."""

    pass


class FAQLocaleUpdate(BaseModel):
    """Schema for updating FAQ locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    question: str | None = Field(default=None, min_length=5, max_length=500)
    answer: str | None = Field(default=None, min_length=1)


class FAQLocaleResponse(FAQLocaleBase):
    """Schema for FAQ locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    faq_id: UUID
    created_at: datetime
    updated_at: datetime


class FAQBase(BaseModel):
    """Base schema for FAQ."""

    category: str | None = Field(default=None, max_length=100)
    is_published: bool = False
    sort_order: int = 0


class FAQCreate(FAQBase):
    """Schema for creating a FAQ."""

    locales: list[FAQLocaleCreate] = Field(..., min_length=1)


class FAQUpdate(BaseModel):
    """Schema for updating a FAQ."""

    category: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class FAQResponse(FAQBase):
    """Schema for FAQ response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    locales: list[FAQLocaleResponse] = []


class FAQPublicResponse(BaseModel):
    """Schema for public FAQ response."""

    id: UUID
    question: str
    answer: str
    category: str | None = None


class FAQListResponse(BaseModel):
    """Schema for FAQ list response."""

    items: list[FAQResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Review Schemas
# ============================================================================


# ============================================================================
# Minimal Response Schemas (to avoid circular dependencies)
# ============================================================================


class CaseMinimalResponse(BaseModel):
    """Minimal case information for review responses (avoids circular dependency)."""

    id: UUID
    slug: str
    title: str
    cover_image_url: str | None = None
    client_name: str | None = None


class ReviewMinimalResponse(BaseModel):
    """Minimal review information for case responses (avoids circular dependency)."""

    id: UUID
    rating: int
    author_name: str
    author_company: str | None = None
    author_position: str | None = None
    author_photo_url: str | None = None
    content: str
    review_date: datetime | None = None


# ============================================================================
# Review Schemas
# ============================================================================


class ReviewStatus(str, Enum):
    """Review moderation status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReviewBase(BaseModel):
    """Base schema for review."""

    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    author_name: str = Field(..., min_length=2, max_length=255)
    author_company: str | None = Field(default=None, max_length=255)
    author_position: str | None = Field(default=None, max_length=255)
    content: str = Field(..., min_length=10)
    is_featured: bool = False
    source: str | None = Field(default=None, max_length=100)
    source_url: str | None = Field(default=None, max_length=500)
    review_date: datetime | None = None
    sort_order: int = 0


class ReviewCreate(ReviewBase):
    """Schema for creating a review.
    
    Note: author_photo_url is managed via POST /admin/reviews/{id}/author-photo endpoint.
    """

    case_id: UUID | None = None


class ReviewUpdate(BaseModel):
    """Schema for updating a review.
    
    Note: author_photo_url is managed via POST/DELETE /admin/reviews/{id}/author-photo endpoints.
    """

    rating: int | None = Field(default=None, ge=1, le=5)
    author_name: str | None = Field(default=None, min_length=2, max_length=255)
    author_company: str | None = None
    author_position: str | None = None
    content: str | None = Field(default=None, min_length=10)
    case_id: UUID | None = None
    is_featured: bool | None = None
    source: str | None = None
    source_url: str | None = None
    review_date: datetime | None = None
    sort_order: int | None = None
    status: ReviewStatus | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class ReviewResponse(ReviewBase):
    """Schema for review response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    author_photo_url: str | None = None
    status: ReviewStatus
    case_id: UUID | None = None
    case: CaseMinimalResponse | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class ReviewPublicResponse(BaseModel):
    """Schema for public review response."""

    id: UUID
    rating: int
    author_name: str
    author_company: str | None = None
    author_position: str | None = None
    author_photo_url: str | None = None
    content: str
    source: str | None = None
    review_date: datetime | None = None
    case: CaseMinimalResponse | None = None


class ReviewListResponse(BaseModel):
    """Schema for review list response."""

    items: list[ReviewResponse]
    total: int
    page: int
    page_size: int


class ReviewPublicListResponse(BaseModel):
    """Schema for public review list response."""

    items: list[ReviewPublicResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Case Schemas
# ============================================================================


class CaseStatus(str, Enum):
    """Case publication status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class CaseLocaleBase(BaseModel):
    """Base schema for case locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    excerpt: str | None = Field(default=None, max_length=500)
    description: str | None = None
    results: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class CaseLocaleCreate(CaseLocaleBase):
    """Schema for creating case locale."""

    pass


class CaseLocaleUpdate(BaseModel):
    """Schema for updating case locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    excerpt: str | None = Field(default=None, max_length=500)
    description: str | None = None
    results: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class CaseLocaleResponse(CaseLocaleBase):
    """Schema for case locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    case_id: UUID
    created_at: datetime
    updated_at: datetime


class CaseServiceLinkResponse(BaseModel):
    """Schema for case-service link response."""

    model_config = ConfigDict(from_attributes=True)

    service_id: UUID
    service: "ServiceResponse | None" = None


class CaseBase(BaseModel):
    """Base schema for case."""

    status: CaseStatus = CaseStatus.DRAFT
    client_name: str | None = Field(default=None, max_length=255)
    project_year: int | None = None
    project_duration: str | None = Field(default=None, max_length=100)
    is_featured: bool = False
    sort_order: int = 0


class CaseCreate(CaseBase):
    """Schema for creating a case.
    
    Note: cover_image_url is managed via POST /admin/cases/{id}/cover-image endpoint.
    """

    locales: list[CaseLocaleCreate] = Field(..., min_length=1)
    service_ids: list[UUID] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    """Schema for updating a case.
    
    Note: cover_image_url is managed via POST/DELETE /admin/cases/{id}/cover-image endpoints.
    """

    status: CaseStatus | None = None
    client_name: str | None = None
    project_year: int | None = None
    project_duration: str | None = None
    is_featured: bool | None = None
    sort_order: int | None = None
    service_ids: list[UUID] | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class CaseResponse(CaseBase):
    """Schema for case response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    cover_image_url: str | None = None
    version: int
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    locales: list[CaseLocaleResponse] = []
    services: list[CaseServiceLinkResponse] = []


class CasePublicResponse(BaseModel):
    """Schema for public case response."""

    id: UUID
    slug: str
    title: str
    excerpt: str | None = None
    description: str | None = None
    results: str | None = None
    cover_image_url: str | None = None
    client_name: str | None = None
    project_year: int | None = None
    project_duration: str | None = None
    is_featured: bool = False
    published_at: datetime | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    services: list[UUID] = []
    reviews: list[ReviewMinimalResponse] = []


class CaseListResponse(BaseModel):
    """Schema for case list response."""

    items: list[CaseResponse]
    total: int
    page: int
    page_size: int


class CasePublicListResponse(BaseModel):
    """Schema for public case list response."""

    items: list[CasePublicResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Bulk Operations Schemas
# ============================================================================


class BulkAction(str, Enum):
    """Bulk operation actions."""

    PUBLISH = "publish"
    UNPUBLISH = "unpublish"
    ARCHIVE = "archive"
    DELETE = "delete"


class BulkResourceType(str, Enum):
    """Resource types for bulk operations."""

    ARTICLES = "articles"
    CASES = "cases"
    REVIEWS = "reviews"
    FAQ = "faq"


class BulkOperationRequest(BaseModel):
    """Schema for bulk operation request."""

    resource_type: BulkResourceType
    action: BulkAction
    ids: list[UUID] = Field(..., min_length=1, max_length=500)


class BulkOperationItemResult(BaseModel):
    """Result for a single item in bulk operation."""

    id: UUID
    status: str  # "success" or "error"
    message: str | None = None


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""

    job_id: UUID | None = None
    status: str  # "completed" or "processing"
    summary: "BulkOperationSummary"


class BulkOperationSummary(BaseModel):
    """Summary of bulk operation results."""

    total: int
    succeeded: int
    failed: int
    details: list[BulkOperationItemResult] = []


# Fix forward references
ArticleResponse.model_rebuild()
CaseResponse.model_rebuild()
BulkOperationResponse.model_rebuild()

