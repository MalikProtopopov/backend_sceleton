"""Mappers for transforming ORM models to DTOs in company module.

This module provides functions to map SQLAlchemy models to Pydantic response schemas.
Keeps business logic (data transformation) out of routers.
"""

from app.core.exceptions import LocaleDataMissingError
from app.modules.company.models import (
    Advantage,
    Employee,
    PracticeArea,
    Service,
)
from app.modules.company.schemas import (
    AdvantagePublicResponse,
    EmployeePublicResponse,
    PracticeAreaPublicResponse,
    ServicePricePublic,
    ServicePublicResponse,
)


# ============================================================================
# Service Mappers
# ============================================================================


def map_service_to_public_response(service: Service, locale: str) -> ServicePublicResponse:
    """Map a Service model to ServicePublicResponse.
    
    Args:
        service: Service ORM model with locales, prices, and tags loaded
        locale: Locale code to filter by (e.g., 'ru', 'en')
        
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
    )


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


def map_employee_to_public_response(employee: Employee, locale: str) -> EmployeePublicResponse:
    """Map an Employee model to EmployeePublicResponse.
    
    Args:
        employee: Employee ORM model with locales loaded
        locale: Locale code to filter by
        
    Returns:
        EmployeePublicResponse with data for the specified locale
    """
    locale_data = next(
        (loc for loc in employee.locales if loc.locale == locale),
        employee.locales[0] if employee.locales else None
    )
    
    if not locale_data:
        raise LocaleDataMissingError("Employee", employee.id, locale)
    
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

