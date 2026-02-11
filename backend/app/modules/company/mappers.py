"""Mappers for transforming ORM models to DTOs in company module.

This module provides functions to map SQLAlchemy models to Pydantic response schemas.
Keeps business logic (data transformation) out of routers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.exceptions import LocaleDataMissingError
from app.modules.company.models import (
    Advantage,
    Employee,
    PracticeArea,
    Service,
)
from app.modules.company.schemas import (
    AdvantagePublicResponse,
    CaseContactForServiceResponse,
    CaseMinimalForServiceResponse,
    ContentBlockForServiceResponse,
    EmployeePublicResponse,
    PracticeAreaPublicResponse,
    ReviewAuthorContactForServiceResponse,
    ReviewMinimalForServiceResponse,
    ServicePricePublic,
    ServicePublicResponse,
)

if TYPE_CHECKING:
    from app.modules.content.models import Case, ContentBlock, Review


# ============================================================================
# Service Mappers
# ============================================================================


def map_service_to_public_response(
    service: Service,
    locale: str,
    cases: list[Case] | None = None,
    reviews: list[Review] | None = None,
    content_blocks: list[ContentBlock] | None = None,
) -> ServicePublicResponse:
    """Map a Service model to ServicePublicResponse.
    
    Args:
        service: Service ORM model with locales, prices, and tags loaded
        locale: Locale code to filter by (e.g., 'ru', 'en')
        cases: Optional list of published cases linked to this service
        reviews: Optional list of approved reviews from cases linked to this service
        content_blocks: Optional list of content blocks to include
        
    Returns:
        ServicePublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in service.locales if loc.locale == locale),
        service.locales[0] if service.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Service", service.id, locale)
    
    # Filter prices for this locale
    prices_for_locale = [
        ServicePricePublic(price=float(p.price), currency=p.currency)
        for p in service.prices
        if p.locale == locale
    ]
    
    # Filter tags for this locale
    tags_for_locale = [t.tag for t in service.tags if t.locale == locale]
    
    # Map cases to minimal response
    cases_response = _map_cases_for_service(cases or [], locale) if cases else []
    
    # Map reviews to minimal response
    reviews_response = _map_reviews_for_service(reviews or []) if reviews else []
    
    # Map content blocks
    blocks_response = [
        ContentBlockForServiceResponse(
            id=b.id,
            locale=b.locale,
            block_type=b.block_type,
            sort_order=b.sort_order,
            title=b.title,
            content=b.content,
            media_url=b.media_url,
            thumbnail_url=b.thumbnail_url,
            link_url=b.link_url,
            link_label=b.link_label,
            device_type=b.device_type,
            block_metadata=b.block_metadata,
        )
        for b in content_blocks
    ] if content_blocks else []
    
    return ServicePublicResponse(
        id=service.id,
        slug=locale_data.slug,
        title=locale_data.title,
        short_description=locale_data.short_description,
        description=locale_data.description,
        icon=service.icon,
        image_url=service.image_url,
        price_from=service.price_from,
        price_currency=service.price_currency,
        prices=prices_for_locale,
        tags=tags_for_locale,
        meta_title=locale_data.meta_title,
        meta_description=locale_data.meta_description,
        cases=cases_response,
        reviews=reviews_response,
        content_blocks=blocks_response,
    )


def _map_cases_for_service(cases: list[Case], locale: str) -> list[CaseMinimalForServiceResponse]:
    """Map cases to minimal response for service detail page.
    
    Args:
        cases: List of Case ORM models with locales loaded
        locale: Locale code to filter by
        
    Returns:
        List of CaseMinimalForServiceResponse
    """
    result = []
    for case in cases:
        locale_data = next(
            (loc for loc in case.locales if loc.locale == locale),
            case.locales[0] if case.locales else None
        )
        if locale_data:
            # Map contacts
            contacts = [
                CaseContactForServiceResponse(
                    id=c.id,
                    contact_type=c.contact_type,
                    value=c.value,
                    sort_order=c.sort_order,
                )
                for c in case.contacts
            ] if case.contacts else []
            
            result.append(CaseMinimalForServiceResponse(
                id=case.id,
                slug=locale_data.slug,
                title=locale_data.title,
                excerpt=locale_data.excerpt,
                cover_image_url=case.cover_image_url,
                client_name=case.client_name,
                project_year=case.project_year,
                project_duration=case.project_duration,
                is_featured=case.is_featured,
                published_at=case.published_at,
                contacts=contacts,
            ))
    return result


def _map_reviews_for_service(reviews: list[Review]) -> list[ReviewMinimalForServiceResponse]:
    """Map reviews to minimal response for service detail page.
    
    Args:
        reviews: List of Review ORM models
        
    Returns:
        List of ReviewMinimalForServiceResponse
    """
    result = []
    for review in reviews:
        # Map author contacts
        author_contacts = [
            ReviewAuthorContactForServiceResponse(
                id=c.id,
                contact_type=c.contact_type,
                value=c.value,
                sort_order=c.sort_order,
            )
            for c in review.author_contacts
        ] if review.author_contacts else []
        
        result.append(ReviewMinimalForServiceResponse(
            id=review.id,
            rating=review.rating,
            author_name=review.author_name,
            author_company=review.author_company,
            author_position=review.author_position,
            author_photo_url=review.author_photo_url,
            content=review.content,
            review_date=review.review_date,
            author_contacts=author_contacts,
        ))
    return result


def map_services_to_public_response(
    services: list[Service], locale: str
) -> list[ServicePublicResponse]:
    """Map a list of Service models to ServicePublicResponse list.
    
    Args:
        services: List of Service ORM models
        locale: Locale code to filter by
        
    Returns:
        List of ServicePublicResponse
    """
    return [map_service_to_public_response(svc, locale) for svc in services]


# ============================================================================
# Employee Mappers
# ============================================================================


def map_employee_to_public_response(
    employee: Employee,
    locale: str,
    content_blocks: list[ContentBlock] | None = None,
) -> EmployeePublicResponse:
    """Map an Employee model to EmployeePublicResponse.
    
    Args:
        employee: Employee ORM model with locales loaded
        locale: Locale code to filter by
        content_blocks: Optional list of content blocks to include
        
    Returns:
        EmployeePublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in employee.locales if loc.locale == locale),
        employee.locales[0] if employee.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Employee", employee.id, locale)
    
    blocks_response = [
        ContentBlockForServiceResponse(
            id=b.id,
            locale=b.locale,
            block_type=b.block_type,
            sort_order=b.sort_order,
            title=b.title,
            content=b.content,
            media_url=b.media_url,
            thumbnail_url=b.thumbnail_url,
            link_url=b.link_url,
            link_label=b.link_label,
            device_type=b.device_type,
            block_metadata=b.block_metadata,
        )
        for b in content_blocks
    ] if content_blocks else []
    
    return EmployeePublicResponse(
        id=employee.id,
        slug=locale_data.slug,
        first_name=locale_data.first_name,
        last_name=locale_data.last_name,
        full_name=locale_data.full_name,
        position=locale_data.position,
        bio=locale_data.bio,
        photo_url=employee.photo_url,
        email=employee.email,
        phone=employee.phone,
        linkedin_url=employee.linkedin_url,
        telegram_url=employee.telegram_url,
        content_blocks=blocks_response,
    )


def map_employees_to_public_response(
    employees: list[Employee], locale: str
) -> list[EmployeePublicResponse]:
    """Map a list of Employee models to EmployeePublicResponse list."""
    return [map_employee_to_public_response(emp, locale) for emp in employees]


# ============================================================================
# PracticeArea Mappers
# ============================================================================


def map_practice_area_to_public_response(
    practice_area: PracticeArea, locale: str
) -> PracticeAreaPublicResponse:
    """Map a PracticeArea model to PracticeAreaPublicResponse.
    
    Args:
        practice_area: PracticeArea ORM model with locales loaded
        locale: Locale code to filter by
        
    Returns:
        PracticeAreaPublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in practice_area.locales if loc.locale == locale),
        practice_area.locales[0] if practice_area.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("PracticeArea", practice_area.id, locale)
    
    return PracticeAreaPublicResponse(
        id=practice_area.id,
        slug=locale_data.slug,
        title=locale_data.title,
        description=locale_data.description,
        icon=practice_area.icon,
    )


def map_practice_areas_to_public_response(
    practice_areas: list[PracticeArea], locale: str
) -> list[PracticeAreaPublicResponse]:
    """Map a list of PracticeArea models to PracticeAreaPublicResponse list."""
    return [map_practice_area_to_public_response(area, locale) for area in practice_areas]


# ============================================================================
# Advantage Mappers
# ============================================================================


def map_advantage_to_public_response(
    advantage: Advantage, locale: str
) -> AdvantagePublicResponse:
    """Map an Advantage model to AdvantagePublicResponse.
    
    Args:
        advantage: Advantage ORM model with locales loaded
        locale: Locale code to filter by
        
    Returns:
        AdvantagePublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in advantage.locales if loc.locale == locale),
        advantage.locales[0] if advantage.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Advantage", advantage.id, locale)
    
    return AdvantagePublicResponse(
        id=advantage.id,
        title=locale_data.title,
        description=locale_data.description,
        icon=advantage.icon,
    )


def map_advantages_to_public_response(
    advantages: list[Advantage], locale: str
) -> list[AdvantagePublicResponse]:
    """Map a list of Advantage models to AdvantagePublicResponse list."""
    return [map_advantage_to_public_response(adv, locale) for adv in advantages]

