"""Pydantic schemas for company module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Service Schemas
# ============================================================================


class ServiceLocaleBase(BaseModel):
    """Base schema for service locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class ServiceLocaleCreate(ServiceLocaleBase):
    """Schema for creating service locale."""

    pass


class ServiceLocaleUpdate(BaseModel):
    """Schema for updating service locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class ServiceLocaleResponse(ServiceLocaleBase):
    """Schema for service locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    created_at: datetime
    updated_at: datetime


class ServicePriceBase(BaseModel):
    """Base schema for service price."""

    locale: str = Field(..., min_length=2, max_length=5)
    price: float = Field(..., ge=0, description="Price value")
    currency: str = Field(default="RUB", max_length=3, description="Currency code (RUB, USD)")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code."""
        v = v.upper()
        if v not in ("RUB", "USD"):
            raise ValueError("Currency must be RUB or USD")
        return v


class ServicePriceCreate(ServicePriceBase):
    """Schema for creating service price."""

    pass


class ServicePriceUpdate(BaseModel):
    """Schema for updating service price."""

    price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=3)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str | None) -> str | None:
        """Validate currency code."""
        if v is not None:
            v = v.upper()
            if v not in ("RUB", "USD"):
                raise ValueError("Currency must be RUB or USD")
        return v


class ServicePriceResponse(ServicePriceBase):
    """Schema for service price response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    created_at: datetime
    updated_at: datetime


class ServiceTagBase(BaseModel):
    """Base schema for service tag."""

    locale: str = Field(..., min_length=2, max_length=5)
    tag: str = Field(..., min_length=1, max_length=100)


class ServiceTagCreate(ServiceTagBase):
    """Schema for creating service tag."""

    pass


class ServiceTagResponse(ServiceTagBase):
    """Schema for service tag response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    created_at: datetime
    updated_at: datetime


class ServiceBase(BaseModel):
    """Base schema for service."""

    icon: str | None = Field(default=None, max_length=100)
    price_from: int | None = Field(default=None, ge=0)
    price_currency: str = Field(default="RUB", max_length=3)
    is_published: bool = False
    sort_order: int = 0


class ServiceCreate(ServiceBase):
    """Schema for creating a service.
    
    Note: image_url is managed via POST /admin/services/{id}/image endpoint.
    """

    locales: list[ServiceLocaleCreate] = Field(..., min_length=1)


class ServiceUpdate(BaseModel):
    """Schema for updating a service.
    
    Note: image_url is managed via POST/DELETE /admin/services/{id}/image endpoints.
    """

    icon: str | None = None
    price_from: int | None = None
    price_currency: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class ServiceResponse(ServiceBase):
    """Schema for service response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    image_url: str | None = None
    version: int
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    locales: list[ServiceLocaleResponse] = []
    prices: list[ServicePriceResponse] = []
    tags: list[ServiceTagResponse] = []


class ServicePricePublic(BaseModel):
    """Public schema for service price."""

    price: float
    currency: str


class ServicePublicResponse(BaseModel):
    """Schema for public service response (single locale)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    short_description: str | None = None
    description: str | None = None
    icon: str | None = None
    image_url: str | None = None
    price_from: int | None = None
    price_currency: str = "RUB"
    prices: list[ServicePricePublic] = Field(default_factory=list, description="List of prices in different currencies")
    tags: list[str] = Field(default_factory=list, description="List of tags for this locale")
    meta_title: str | None = None
    meta_description: str | None = None


class ServiceListResponse(BaseModel):
    """Schema for service list response."""

    items: list[ServiceResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Employee Schemas
# ============================================================================


class EmployeeLocaleBase(BaseModel):
    """Base schema for employee locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=2, max_length=255)
    position: str = Field(..., min_length=1, max_length=255)
    bio: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class EmployeeLocaleCreate(EmployeeLocaleBase):
    """Schema for creating employee locale."""

    pass


class EmployeeLocaleUpdate(BaseModel):
    """Schema for updating employee locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    position: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = None
    meta_title: str | None = Field(default=None, max_length=70)
    meta_description: str | None = Field(default=None, max_length=160)


class EmployeeLocaleResponse(EmployeeLocaleBase):
    """Schema for employee locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    full_name: str
    created_at: datetime
    updated_at: datetime


class EmployeeBase(BaseModel):
    """Base schema for employee."""

    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    telegram_url: str | None = Field(default=None, max_length=500)
    is_published: bool = False
    sort_order: int = 0


class EmployeeCreate(EmployeeBase):
    """Schema for creating an employee.
    
    Note: photo_url is managed via POST /admin/employees/{id}/photo endpoint.
    """

    locales: list[EmployeeLocaleCreate] = Field(..., min_length=1)
    practice_area_ids: list[UUID] = Field(default_factory=list)


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee.

    Note: photo_url is managed via POST/DELETE /admin/employees/{id}/photo endpoints.
    """

    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    telegram_url: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    practice_area_ids: list[UUID] | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class EmployeeResponse(EmployeeBase):
    """Schema for employee response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    photo_url: str | None = None
    version: int
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    locales: list[EmployeeLocaleResponse] = []


class EmployeePublicResponse(BaseModel):
    """Schema for public employee response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    first_name: str
    last_name: str
    full_name: str
    position: str
    bio: str | None = None
    photo_url: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    telegram_url: str | None = None


class EmployeeListResponse(BaseModel):
    """Schema for employee list response."""

    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Practice Area Schemas
# ============================================================================


class PracticeAreaLocaleBase(BaseModel):
    """Base schema for practice area locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=255)
    description: str | None = None


class PracticeAreaLocaleCreate(PracticeAreaLocaleBase):
    """Schema for creating practice area locale."""

    pass


class PracticeAreaLocaleUpdate(BaseModel):
    """Schema for updating practice area locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None


class PracticeAreaLocaleResponse(PracticeAreaLocaleBase):
    """Schema for practice area locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    practice_area_id: UUID
    created_at: datetime
    updated_at: datetime


class PracticeAreaBase(BaseModel):
    """Base schema for practice area."""

    icon: str | None = Field(default=None, max_length=100)
    is_published: bool = False
    sort_order: int = 0


class PracticeAreaCreate(PracticeAreaBase):
    """Schema for creating a practice area."""

    locales: list[PracticeAreaLocaleCreate] = Field(..., min_length=1)


class PracticeAreaUpdate(BaseModel):
    """Schema for updating a practice area."""

    icon: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class PracticeAreaResponse(PracticeAreaBase):
    """Schema for practice area response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    locales: list[PracticeAreaLocaleResponse] = []


class PracticeAreaPublicResponse(BaseModel):
    """Schema for public practice area response."""

    id: UUID
    slug: str
    title: str
    description: str | None = None
    icon: str | None = None


class PracticeAreaListResponse(BaseModel):
    """Schema for practice area list response."""

    items: list[PracticeAreaResponse]
    total: int


# ============================================================================
# Advantage Schemas
# ============================================================================


class AdvantageLocaleBase(BaseModel):
    """Base schema for advantage locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class AdvantageLocaleCreate(AdvantageLocaleBase):
    """Schema for creating advantage locale."""

    pass


class AdvantageLocaleUpdate(BaseModel):
    """Schema for updating advantage locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class AdvantageLocaleResponse(AdvantageLocaleBase):
    """Schema for advantage locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    advantage_id: UUID
    created_at: datetime
    updated_at: datetime


class AdvantageBase(BaseModel):
    """Base schema for advantage."""

    icon: str | None = Field(default=None, max_length=100)
    is_published: bool = False
    sort_order: int = 0


class AdvantageCreate(AdvantageBase):
    """Schema for creating an advantage."""

    locales: list[AdvantageLocaleCreate] = Field(..., min_length=1)


class AdvantageUpdate(BaseModel):
    """Schema for updating an advantage."""

    icon: str | None = None
    is_published: bool | None = None
    sort_order: int | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class AdvantageResponse(AdvantageBase):
    """Schema for advantage response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    locales: list[AdvantageLocaleResponse] = []


class AdvantagePublicResponse(BaseModel):
    """Schema for public advantage response."""

    id: UUID
    title: str
    description: str | None = None
    icon: str | None = None


class AdvantageListResponse(BaseModel):
    """Schema for advantage list response."""

    items: list[AdvantageResponse]
    total: int


# ============================================================================
# Contact Schemas
# ============================================================================


class AddressLocaleBase(BaseModel):
    """Base schema for address locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    name: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    street: str = Field(..., max_length=255)
    building: str | None = Field(default=None, max_length=50)
    postal_code: str | None = Field(default=None, max_length=20)


class AddressLocaleCreate(AddressLocaleBase):
    """Schema for creating address locale."""

    pass


class AddressLocaleUpdate(BaseModel):
    """Schema for updating address locale."""

    locale: str = Field(..., min_length=2, max_length=5)
    name: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    street: str | None = Field(default=None, max_length=255)
    building: str | None = Field(default=None, max_length=50)
    postal_code: str | None = Field(default=None, max_length=20)


class AddressLocaleResponse(AddressLocaleBase):
    """Schema for address locale response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    address_id: UUID
    full_address: str
    created_at: datetime
    updated_at: datetime


class AddressBase(BaseModel):
    """Base schema for address."""

    address_type: str = Field(default="office", max_length=20)
    latitude: float | None = None
    longitude: float | None = None
    working_hours: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    is_primary: bool = False
    sort_order: int = 0


class AddressCreate(AddressBase):
    """Schema for creating an address."""

    locales: list[AddressLocaleCreate] = Field(..., min_length=1)


class AddressUpdate(BaseModel):
    """Schema for updating an address."""

    address_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    working_hours: str | None = None
    phone: str | None = None
    email: str | None = None
    is_primary: bool | None = None
    sort_order: int | None = None


class AddressResponse(AddressBase):
    """Schema for address response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    locales: list[AddressLocaleResponse] = []


class ContactBase(BaseModel):
    """Base schema for contact."""

    contact_type: str = Field(..., max_length=20)
    value: str = Field(..., max_length=255)
    label: str | None = Field(default=None, max_length=100)
    icon: str | None = Field(default=None, max_length=100)
    is_primary: bool = False
    sort_order: int = 0


class AddressListResponse(BaseModel):
    """Schema for address list response."""

    items: list[AddressResponse]
    total: int


class ContactCreate(ContactBase):
    """Schema for creating a contact."""

    pass


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""

    contact_type: str | None = None
    value: str | None = None
    label: str | None = None
    icon: str | None = None
    is_primary: bool | None = None
    sort_order: int | None = None


class ContactResponse(ContactBase):
    """Schema for contact response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


class ContactListResponse(BaseModel):
    """Schema for contact list response."""

    items: list[ContactResponse]
    total: int


class ContactsPublicResponse(BaseModel):
    """Schema for public contacts response."""

    addresses: list[AddressResponse] = []
    contacts: list[ContactResponse] = []

