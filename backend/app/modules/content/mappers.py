"""Mappers for transforming ORM models to DTOs in content module.

This module provides functions to map SQLAlchemy models to Pydantic response schemas.
Keeps business logic (data transformation) out of routers.
"""

from app.core.exceptions import LocaleDataMissingError
from app.modules.content.models import (
    Article,
    Case,
    FAQ,
    Topic,
)
from app.modules.content.schemas import (
    ArticlePublicResponse,
    CasePublicResponse,
    FAQPublicResponse,
    TopicDetailPublicResponse,
    TopicPublicResponse,
    TopicWithArticlesCountPublicResponse,
)


# ============================================================================
# Topic Mappers
# ============================================================================


def map_topic_to_public_response(topic: Topic, locale: str) -> TopicPublicResponse:
    """Map a Topic model to TopicPublicResponse.
    
    Args:
        topic: Topic ORM model with locales loaded
        locale: Locale code to filter by
        
    Returns:
        TopicPublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in topic.locales if loc.locale == locale),
        topic.locales[0] if topic.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Topic", topic.id, locale)
    
    return TopicPublicResponse(
        id=topic.id,
        slug=locale_data.slug,
        title=locale_data.title,
        description=locale_data.description,
        icon=topic.icon,
        color=topic.color,
    )


def map_topics_to_public_response(
    topics: list[Topic], locale: str
) -> list[TopicPublicResponse]:
    """Map a list of Topic models to TopicPublicResponse list."""
    return [map_topic_to_public_response(t, locale) for t in topics]


def map_topic_with_count_to_public_response(
    topic: Topic, locale: str, articles_count: int
) -> TopicWithArticlesCountPublicResponse:
    """Map a Topic model with article count to TopicWithArticlesCountPublicResponse.
    
    Args:
        topic: Topic ORM model with locales loaded
        locale: Locale code to filter by
        articles_count: Number of published articles in this topic
        
    Returns:
        TopicWithArticlesCountPublicResponse
    """
    locale_data = next(
        (loc for loc in topic.locales if loc.locale == locale),
        topic.locales[0] if topic.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Topic", topic.id, locale)
    
    return TopicWithArticlesCountPublicResponse(
        id=topic.id,
        slug=locale_data.slug,
        title=locale_data.title,
        description=locale_data.description,
        icon=topic.icon,
        color=topic.color,
        articles_count=articles_count,
    )


def map_topics_with_counts_to_public_response(
    topics_with_counts: list[tuple[Topic, int]], locale: str
) -> list[TopicWithArticlesCountPublicResponse]:
    """Map a list of (Topic, count) tuples to TopicWithArticlesCountPublicResponse list."""
    return [
        map_topic_with_count_to_public_response(topic, locale, count)
        for topic, count in topics_with_counts
    ]


def map_topic_to_detail_public_response(
    topic: Topic, locale: str, articles_count: int
) -> TopicDetailPublicResponse:
    """Map a Topic model to TopicDetailPublicResponse with SEO fields.
    
    Args:
        topic: Topic ORM model with locales loaded
        locale: Locale code to filter by
        articles_count: Number of published articles in this topic
        
    Returns:
        TopicDetailPublicResponse with SEO fields
    """
    locale_data = next(
        (loc for loc in topic.locales if loc.locale == locale),
        topic.locales[0] if topic.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Topic", topic.id, locale)
    
    return TopicDetailPublicResponse(
        id=topic.id,
        slug=locale_data.slug,
        title=locale_data.title,
        description=locale_data.description,
        icon=topic.icon,
        color=topic.color,
        meta_title=locale_data.meta_title,
        meta_description=locale_data.meta_description,
        meta_keywords=locale_data.meta_keywords,
        og_image=locale_data.og_image,
        articles_count=articles_count,
    )


# ============================================================================
# Article Mappers
# ============================================================================


def map_article_to_public_response(
    article: Article, locale: str, include_content: bool = True
) -> ArticlePublicResponse:
    """Map an Article model to ArticlePublicResponse.
    
    Args:
        article: Article ORM model with locales and topics loaded
        locale: Locale code to filter by
        include_content: Whether to include full content (False for list views)
        
    Returns:
        ArticlePublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in article.locales if loc.locale == locale),
        article.locales[0] if article.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Article", article.id, locale)
    
    # Get topics for this locale
    topics_response = []
    for article_topic in article.topics:
        topic = article_topic.topic
        topic_locale = next(
            (loc for loc in topic.locales if loc.locale == locale), None
        )
        if topic_locale:
            topics_response.append(TopicPublicResponse(
                id=topic.id,
                slug=topic_locale.slug,
                title=topic_locale.title,
                description=topic_locale.description,
                icon=topic.icon,
                color=topic.color,
            ))
    
    return ArticlePublicResponse(
        id=article.id,
        slug=locale_data.slug,
        title=locale_data.title,
        excerpt=locale_data.excerpt,
        content=locale_data.content if include_content else None,
        cover_image_url=article.cover_image_url,
        reading_time_minutes=article.reading_time_minutes,
        published_at=article.published_at,
        meta_title=locale_data.meta_title,
        meta_description=locale_data.meta_description,
        topics=topics_response,
    )


def map_articles_to_public_response(
    articles: list[Article], locale: str, include_content: bool = False
) -> list[ArticlePublicResponse]:
    """Map a list of Article models to ArticlePublicResponse list.
    
    Note: By default, content is not included in list views.
    """
    return [
        map_article_to_public_response(article, locale, include_content)
        for article in articles
    ]


# ============================================================================
# FAQ Mappers
# ============================================================================


def map_faq_to_public_response(faq: FAQ, locale: str) -> FAQPublicResponse:
    """Map a FAQ model to FAQPublicResponse.
    
    Args:
        faq: FAQ ORM model with locales loaded
        locale: Locale code to filter by
        
    Returns:
        FAQPublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in faq.locales if loc.locale == locale),
        faq.locales[0] if faq.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("FAQ", faq.id, locale)
    
    return FAQPublicResponse(
        id=faq.id,
        question=locale_data.question,
        answer=locale_data.answer,
        category=faq.category,
    )


def map_faqs_to_public_response(
    faqs: list[FAQ], locale: str
) -> list[FAQPublicResponse]:
    """Map a list of FAQ models to FAQPublicResponse list."""
    return [map_faq_to_public_response(faq, locale) for faq in faqs]


# ============================================================================
# Case Mappers
# ============================================================================


def map_case_to_public_response(
    case: Case, locale: str, include_full_content: bool = True
) -> CasePublicResponse:
    """Map a Case model to CasePublicResponse.
    
    Args:
        case: Case ORM model with locales and services loaded
        locale: Locale code to filter by
        include_full_content: Whether to include full description/results (False for lists)
        
    Returns:
        CasePublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in case.locales if loc.locale == locale),
        case.locales[0] if case.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Case", case.id, locale)
    
    return CasePublicResponse(
        id=case.id,
        slug=locale_data.slug,
        title=locale_data.title,
        excerpt=locale_data.excerpt,
        description=locale_data.description if include_full_content else None,
        results=locale_data.results if include_full_content else None,
        cover_image_url=case.cover_image_url,
        client_name=case.client_name,
        project_year=case.project_year,
        project_duration=case.project_duration,
        is_featured=case.is_featured,
        published_at=case.published_at,
        meta_title=locale_data.meta_title,
        meta_description=locale_data.meta_description,
        services=[s.service_id for s in case.services],
    )


def map_cases_to_public_response(
    cases: list[Case], locale: str, include_full_content: bool = False
) -> list[CasePublicResponse]:
    """Map a list of Case models to CasePublicResponse list.
    
    Note: By default, full content is not included in list views.
    """
    return [
        map_case_to_public_response(case, locale, include_full_content)
        for case in cases
    ]

