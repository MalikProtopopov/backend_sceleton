"""Shared Pydantic schemas used across multiple modules."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated list response.

    Usage::

        class ProductListResponse(PaginatedResponse[ProductResponse]):
            pass

    Or directly::

        PaginatedResponse[ProductResponse]
    """

    items: list[T]
    total: int
    page: int
    page_size: int
