"""Helpers for locale management across models."""

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundError, SlugAlreadyExistsError

# Type variable for locale models
LocaleModel = TypeVar("LocaleModel")


class MinimumLocalesError(AppException):
    """Cannot delete the last locale - at least one is required."""

    def __init__(self, resource: str) -> None:
        from fastapi import status
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="minimum_locales_required",
            message=f"Cannot delete the last locale. {resource} must have at least one locale.",
            detail={"resource": resource},
        )


class LocaleAlreadyExistsError(AppException):
    """Locale with this language already exists for this resource."""

    def __init__(self, resource: str, locale: str) -> None:
        from fastapi import status
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="locale_already_exists",
            message=f"{resource} already has a locale for language '{locale}'",
            detail={"resource": resource, "locale": locale},
        )


async def check_slug_unique(
    db: AsyncSession,
    locale_model: type,
    parent_model: type,
    parent_id_field: str,
    slug: str,
    locale: str,
    tenant_id: UUID,
    exclude_locale_id: UUID | None = None,
    exclude_parent_id: UUID | None = None,
) -> None:
    """Check if slug is unique within tenant and locale.
    
    Args:
        db: Database session
        locale_model: The locale model class (e.g., ServiceLocale)
        parent_model: The parent model class (e.g., Service)
        parent_id_field: Name of the foreign key field (e.g., "service_id")
        slug: Slug to check
        locale: Locale code (e.g., "ru", "en")
        tenant_id: Tenant ID
        exclude_locale_id: Locale ID to exclude (for updates to specific locale)
        exclude_parent_id: Parent ID to exclude (for updates to any locale of the parent)
    """
    stmt = (
        select(locale_model)
        .join(parent_model)
        .where(parent_model.tenant_id == tenant_id)
        .where(parent_model.deleted_at.is_(None))
        .where(locale_model.locale == locale)
        .where(locale_model.slug == slug)
    )
    
    if exclude_locale_id:
        stmt = stmt.where(locale_model.id != exclude_locale_id)
    
    if exclude_parent_id:
        stmt = stmt.where(parent_model.id != exclude_parent_id)
    
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise SlugAlreadyExistsError(slug, locale)


async def check_locale_exists(
    db: AsyncSession,
    locale_model: type,
    parent_id_field: str,
    parent_id: UUID,
    locale: str,
) -> bool:
    """Check if locale already exists for parent entity.
    
    Args:
        db: Database session
        locale_model: The locale model class
        parent_id_field: Name of the foreign key field
        parent_id: Parent entity ID
        locale: Locale code to check
        
    Returns:
        True if locale exists, False otherwise
    """
    stmt = (
        select(locale_model)
        .where(getattr(locale_model, parent_id_field) == parent_id)
        .where(locale_model.locale == locale)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_locale_by_id(
    db: AsyncSession,
    locale_model: type,
    locale_id: UUID,
    parent_id_field: str,
    parent_id: UUID,
    resource_name: str,
) -> Any:
    """Get locale by ID with parent validation.
    
    Args:
        db: Database session
        locale_model: The locale model class
        locale_id: Locale ID to find
        parent_id_field: Name of the foreign key field
        parent_id: Parent entity ID
        resource_name: Human-readable resource name for error messages
        
    Returns:
        Locale object
        
    Raises:
        NotFoundError: If locale not found
    """
    stmt = (
        select(locale_model)
        .where(locale_model.id == locale_id)
        .where(getattr(locale_model, parent_id_field) == parent_id)
    )
    result = await db.execute(stmt)
    locale_obj = result.scalar_one_or_none()
    
    if not locale_obj:
        raise NotFoundError(f"{resource_name}Locale", locale_id)
    
    return locale_obj


async def count_locales(
    db: AsyncSession,
    locale_model: type,
    parent_id_field: str,
    parent_id: UUID,
) -> int:
    """Count locales for parent entity.
    
    Args:
        db: Database session
        locale_model: The locale model class
        parent_id_field: Name of the foreign key field
        parent_id: Parent entity ID
        
    Returns:
        Number of locales
    """
    from sqlalchemy import func
    
    stmt = (
        select(func.count())
        .select_from(locale_model)
        .where(getattr(locale_model, parent_id_field) == parent_id)
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


def update_locale_fields(locale_obj: Any, data: Any, fields: list[str]) -> None:
    """Update locale object fields from data.
    
    Args:
        locale_obj: Locale object to update
        data: Update data (Pydantic model)
        fields: List of field names to update
    """
    for field in fields:
        value = getattr(data, field, None)
        if value is not None:
            setattr(locale_obj, field, value)

