"""Content module database models."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import (
    Base,
    SEOMixin,
    SlugMixin,
    SoftDeleteMixin,
    SortOrderMixin,
    TenantMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)


class ArticleStatus(str, Enum):
    """Article publication status."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ============================================================================
# Topics / Categories
# ============================================================================


class Topic(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Topic / category for articles."""

    __tablename__ = "topics"

    # Icon or image
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # #RRGGBB

    # Relations
    locales: Mapped[list["TopicLocale"]] = relationship(
        "TopicLocale",
        back_populates="topic",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    articles: Mapped[list["ArticleTopic"]] = relationship(
        "ArticleTopic",
        back_populates="topic",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_topics_tenant", "tenant_id"),
        CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_topics_color_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<Topic {self.id}>"


class TopicLocale(Base, UUIDMixin, TimestampMixin, SlugMixin, SEOMixin):
    """Localized content for topics."""

    __tablename__ = "topic_locales"

    topic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relation
    topic: Mapped["Topic"] = relationship("Topic", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("topic_id", "locale", name="uq_topic_locales"),
        Index("ix_topic_locales_slug", "locale", "slug"),
    )


# ============================================================================
# Articles
# ============================================================================


class Article(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Article / blog post."""

    __tablename__ = "articles"

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=ArticleStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    # Publishing dates
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Featured image
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Reading time in minutes (calculated)
    reading_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # View count (for analytics)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Author reference
    author_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relations
    locales: Mapped[list["ArticleLocale"]] = relationship(
        "ArticleLocale",
        back_populates="article",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    topics: Mapped[list["ArticleTopic"]] = relationship(
        "ArticleTopic",
        back_populates="article",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_articles_tenant", "tenant_id"),
        Index(
            "ix_articles_published",
            "tenant_id",
            "status",
            postgresql_where="deleted_at IS NULL AND status = 'published'",
        ),
        Index("ix_articles_author", "author_id"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_articles_status",
        ),
    )

    @property
    def is_published(self) -> bool:
        return self.status == ArticleStatus.PUBLISHED.value

    def publish(self) -> None:
        """Publish the article."""
        self.status = ArticleStatus.PUBLISHED.value
        if not self.published_at:
            self.published_at = datetime.utcnow()

    def unpublish(self) -> None:
        """Move article to draft."""
        self.status = ArticleStatus.DRAFT.value

    def archive(self) -> None:
        """Archive the article."""
        self.status = ArticleStatus.ARCHIVED.value

    def __repr__(self) -> str:
        return f"<Article {self.id} status={self.status}>"


class ArticleLocale(Base, UUIDMixin, TimestampMixin, SlugMixin, SEOMixin):
    """Localized content for articles."""

    __tablename__ = "article_locales"

    article_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relation
    article: Mapped["Article"] = relationship("Article", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("article_id", "locale", name="uq_article_locales"),
        Index("ix_article_locales_slug", "locale", "slug"),
        CheckConstraint("char_length(title) >= 1", name="ck_article_locales_title"),
        CheckConstraint("char_length(slug) >= 2", name="ck_article_locales_slug"),
    )


class ArticleTopic(Base, UUIDMixin):
    """Many-to-many between articles and topics."""

    __tablename__ = "article_topics"

    article_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relations
    article: Mapped["Article"] = relationship("Article", back_populates="topics")
    topic: Mapped["Topic"] = relationship("Topic", back_populates="articles")

    __table_args__ = (
        UniqueConstraint("article_id", "topic_id", name="uq_article_topics"),
    )


# ============================================================================
# FAQ
# ============================================================================


class FAQ(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Frequently asked question."""

    __tablename__ = "faqs"

    # Category (optional grouping)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Is visible
    is_published: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relations
    locales: Mapped[list["FAQLocale"]] = relationship(
        "FAQLocale",
        back_populates="faq",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_faqs_tenant", "tenant_id"),
        Index(
            "ix_faqs_published",
            "tenant_id",
            "is_published",
            postgresql_where="deleted_at IS NULL AND is_published = true",
        ),
        Index("ix_faqs_category", "tenant_id", "category"),
    )


class FAQLocale(Base, UUIDMixin, TimestampMixin):
    """Localized content for FAQ."""

    __tablename__ = "faq_locales"

    faq_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("faqs.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Relation
    faq: Mapped["FAQ"] = relationship("FAQ", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("faq_id", "locale", name="uq_faq_locales"),
        CheckConstraint("char_length(question) >= 5", name="ck_faq_locales_question"),
    )


# ============================================================================
# Cases (Portfolio / Case Studies)
# ============================================================================


class Case(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Case study / portfolio item."""

    __tablename__ = "cases"

    # Status (similar to articles)
    status: Mapped[str] = mapped_column(
        String(20),
        default=ArticleStatus.DRAFT.value,
        nullable=False,
        index=True,
    )

    # Publishing
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Featured image
    cover_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Client name (optional, for confidential cases)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Project details
    project_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Featured / highlighted
    is_featured: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Relations
    locales: Mapped[list["CaseLocale"]] = relationship(
        "CaseLocale",
        back_populates="case",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    services: Mapped[list["CaseServiceLink"]] = relationship(
        "CaseServiceLink",
        back_populates="case",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review",
        back_populates="case",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_cases_tenant", "tenant_id"),
        Index(
            "ix_cases_published",
            "tenant_id",
            "status",
            postgresql_where="deleted_at IS NULL AND status = 'published'",
        ),
        Index("ix_cases_featured", "tenant_id", "is_featured"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_cases_status",
        ),
    )

    @property
    def is_published(self) -> bool:
        return self.status == ArticleStatus.PUBLISHED.value

    def __repr__(self) -> str:
        return f"<Case {self.id} status={self.status}>"


class CaseLocale(Base, UUIDMixin, TimestampMixin, SlugMixin, SEOMixin):
    """Localized content for cases."""

    __tablename__ = "case_locales"

    case_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    locale: Mapped[str] = mapped_column(String(5), nullable=False)

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Results / outcomes
    results: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relation
    case: Mapped["Case"] = relationship("Case", back_populates="locales")

    __table_args__ = (
        UniqueConstraint("case_id", "locale", name="uq_case_locales"),
        Index("ix_case_locales_slug", "locale", "slug"),
    )


class CaseServiceLink(Base, UUIDMixin):
    """Many-to-many between cases and services."""

    __tablename__ = "case_service_links"

    case_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relations
    case: Mapped["Case"] = relationship("Case", back_populates="services")

    __table_args__ = (
        UniqueConstraint("case_id", "service_id", name="uq_case_service_links"),
    )


# ============================================================================
# Reviews (Social Proof / Testimonials)
# ============================================================================


class ReviewStatus(str, Enum):
    """Review moderation status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Review(
    Base, UUIDMixin, TimestampMixin, SoftDeleteMixin, TenantMixin,
    VersionMixin, SortOrderMixin
):
    """Customer review / testimonial.
    
    Reviews require moderation before being displayed publicly.
    Can optionally be linked to a specific case study.
    """

    __tablename__ = "reviews"

    # Moderation status
    status: Mapped[str] = mapped_column(
        String(20),
        default=ReviewStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    # Rating (1-5 stars)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)

    # Author information
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Review content
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional link to case study
    case_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Featured / highlighted
    is_featured: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Source (where the review came from)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # google, clutch, etc.
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Date of review (can be different from created_at)
    review_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relations
    case: Mapped["Case | None"] = relationship("Case", back_populates="reviews")

    __table_args__ = (
        Index("ix_reviews_tenant", "tenant_id"),
        Index(
            "ix_reviews_approved",
            "tenant_id",
            "status",
            postgresql_where="deleted_at IS NULL AND status = 'approved'",
        ),
        Index("ix_reviews_featured", "tenant_id", "is_featured"),
        Index("ix_reviews_case", "case_id"),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_reviews_rating_range",
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_reviews_status",
        ),
        CheckConstraint(
            "char_length(author_name) >= 2",
            name="ck_reviews_author_name",
        ),
        CheckConstraint(
            "char_length(content) >= 10",
            name="ck_reviews_content_min",
        ),
    )

    @property
    def is_approved(self) -> bool:
        return self.status == ReviewStatus.APPROVED.value

    def approve(self) -> None:
        """Approve the review."""
        self.status = ReviewStatus.APPROVED.value

    def reject(self) -> None:
        """Reject the review."""
        self.status = ReviewStatus.REJECTED.value

    def __repr__(self) -> str:
        return f"<Review {self.id} status={self.status} rating={self.rating}>"

