"""Create content tables.

Revision ID: 005
Revises: 004
Create Date: 2026-01-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create content module tables."""
    
    # Topics table
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_topics_color_format"),
    )
    op.create_index("ix_topics_tenant", "topics", ["tenant_id"])

    # Topic locales
    op.create_table(
        "topic_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(70), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("meta_keywords", sa.String(255), nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("topic_id", "locale", name="uq_topic_locales"),
    )
    op.create_index("ix_topic_locales_slug", "topic_locales", ["locale", "slug"])

    # Articles table
    op.create_table(
        "articles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cover_image_url", sa.String(500), nullable=True),
        sa.Column("reading_time_minutes", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, default=0),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_articles_status"),
    )
    op.create_index("ix_articles_tenant", "articles", ["tenant_id"])
    op.create_index("ix_articles_published", "articles", ["tenant_id", "status"], postgresql_where="deleted_at IS NULL AND status = 'published'")
    op.create_index("ix_articles_author", "articles", ["author_id"])

    # Article locales
    op.create_table(
        "article_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("excerpt", sa.String(500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(70), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("meta_keywords", sa.String(255), nullable=True),
        sa.Column("og_image", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("article_id", "locale", name="uq_article_locales"),
        sa.CheckConstraint("char_length(title) >= 1", name="ck_article_locales_title"),
        sa.CheckConstraint("char_length(slug) >= 2", name="ck_article_locales_slug"),
    )
    op.create_index("ix_article_locales_slug", "article_locales", ["locale", "slug"])

    # Article topics (many-to-many)
    op.create_table(
        "article_topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("article_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("article_id", "topic_id", name="uq_article_topics"),
    )

    # FAQs table
    op.create_table(
        "faqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, default=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, default=0),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_faqs_tenant", "faqs", ["tenant_id"])
    op.create_index("ix_faqs_published", "faqs", ["tenant_id", "is_published"], postgresql_where="deleted_at IS NULL AND is_published = true")
    op.create_index("ix_faqs_category", "faqs", ["tenant_id", "category"])

    # FAQ locales
    op.create_table(
        "faq_locales",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("faq_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("faqs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("locale", sa.String(5), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("faq_id", "locale", name="uq_faq_locales"),
        sa.CheckConstraint("char_length(question) >= 5", name="ck_faq_locales_question"),
    )


def downgrade() -> None:
    """Drop content tables."""
    op.drop_table("faq_locales")
    op.drop_table("faqs")
    op.drop_table("article_topics")
    op.drop_table("article_locales")
    op.drop_table("articles")
    op.drop_table("topic_locales")
    op.drop_table("topics")

