"""Content module database models."""

from datetime import UTC, datetime
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
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
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
            self.published_at = datetime.now(UTC)

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
    contacts: Mapped[list["CaseContact"]] = relationship(
        "CaseContact",
        back_populates="case",
        lazy="selectin",
        cascade="all, delete-orphan",
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

    @property
    def slug(self) -> str:
        """Get slug from default locale (first available)."""
        if self.locales:
            return self.locales[0].slug
        return ""

    @property
    def title(self) -> str:
        """Get title from default locale (first available)."""
        if self.locales:
            return self.locales[0].title
        return ""

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
    service: Mapped["Service"] = relationship("Service", foreign_keys=[service_id])

    __table_args__ = (
        UniqueConstraint("case_id", "service_id", name="uq_case_service_links"),
        Index("ix_case_service_links_case", "case_id"),
        Index("ix_case_service_links_service", "service_id"),
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
    author_contacts: Mapped[list["ReviewAuthorContact"]] = relationship(
        "ReviewAuthorContact",
        back_populates="review",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

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


# ============================================================================
# Contacts for Cases and Reviews
# ============================================================================


class CaseContact(Base, UUIDMixin, SortOrderMixin):
    """Contact links for case client (company website, social media).
    
    Used to store contact information for the client/company featured in a case study.
    Supports various contact types: website, social media, email, phone, etc.
    """

    __tablename__ = "case_contacts"

    case_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Contact type: website, instagram, telegram, linkedin, facebook, twitter, 
    # youtube, tiktok, email, phone, whatsapp, viber, other
    contact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Contact value: URL, phone number, email, username, etc.
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relations
    case: Mapped["Case"] = relationship("Case", back_populates="contacts")

    __table_args__ = (
        Index("ix_case_contacts_case", "case_id"),
    )

    def __repr__(self) -> str:
        return f"<CaseContact {self.id} type={self.contact_type}>"


class ReviewAuthorContact(Base, UUIDMixin, SortOrderMixin):
    """Contact links for review author.
    
    Used to store contact information for the person who wrote the review.
    Supports various contact types: website, social media, email, phone, etc.
    """

    __tablename__ = "review_author_contacts"

    review_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Contact type: website, instagram, telegram, linkedin, facebook, twitter,
    # youtube, tiktok, email, phone, whatsapp, viber, other
    contact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Contact value: URL, phone number, email, username, etc.
    value: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relations
    review: Mapped["Review"] = relationship("Review", back_populates="author_contacts")

    __table_args__ = (
        Index("ix_review_author_contacts_review", "review_id"),
    )

    def __repr__(self) -> str:
        return f"<ReviewAuthorContact {self.id} type={self.contact_type}>"


# ============================================================================
# Content Blocks (Flexible Content System)
# ============================================================================


class ContentBlockType(str, Enum):
    """Type of content block."""

    TEXT = "text"  # HTML text content
    IMAGE = "image"  # Single image
    VIDEO = "video"  # Video (YouTube, RuTube, etc.)
    GALLERY = "gallery"  # Image gallery/slider
    LINK = "link"  # Link (website, TG bot, etc.)
    RESULT = "result"  # Result block (for cases)


class DeviceType(str, Enum):
    """Device type for responsive content."""

    MOBILE = "mobile"
    DESKTOP = "desktop"
    BOTH = "both"


class EntityType(str, Enum):
    """Entity type for content blocks."""

    ARTICLE = "article"
    CASE = "case"
    SERVICE = "service"


class ContentBlock(Base, UUIDMixin, TimestampMixin, TenantMixin, SortOrderMixin):
    """Flexible content block for articles, cases, and services.
    
    Allows creating structured content with different block types:
    - text: HTML content
    - image: Single image with alt text and caption
    - video: Embedded video (YouTube, RuTube, etc.)
    - gallery: Image slider/gallery
    - link: Link to external resource (website, TG bot, etc.)
    - result: Result block with video, link, and text (for cases)
    
    Each block can be localized and sorted independently.
    """

    __tablename__ = "content_blocks"

    # Polymorphic relationship
    entity_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Entity type: article, case, service",
    )
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment="ID of the related entity",
    )
    locale: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        comment="Locale code: ru, en, etc.",
    )

    # Block type
    block_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Block type: text, image, video, gallery, link, result",
    )

    # Content fields
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional block title/heading",
    )
    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="HTML content for text blocks",
    )
    media_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL for image or video",
    )
    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Thumbnail URL for video blocks",
    )
    link_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Link URL for link/result blocks",
    )
    link_label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Link button text",
    )
    device_type: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        default=DeviceType.BOTH.value,
        comment="Device type: mobile, desktop, both",
    )
    block_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional metadata (alt, caption, images[], provider, icon)",
    )

    __table_args__ = (
        Index("ix_content_blocks_tenant", "tenant_id"),
        Index("ix_content_blocks_entity", "entity_type", "entity_id", "locale"),
        Index(
            "ix_content_blocks_entity_sorted",
            "entity_type",
            "entity_id",
            "locale",
            "sort_order",
        ),
        CheckConstraint(
            "entity_type IN ('article', 'case', 'service', 'employee', 'product')",
            name="ck_content_blocks_entity_type",
        ),
        CheckConstraint(
            "block_type IN ('text', 'image', 'video', 'gallery', 'link', 'result')",
            name="ck_content_blocks_block_type",
        ),
        CheckConstraint(
            "device_type IS NULL OR device_type IN ('mobile', 'desktop', 'both')",
            name="ck_content_blocks_device_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<ContentBlock {self.id} {self.entity_type}/{self.entity_id} type={self.block_type}>"

