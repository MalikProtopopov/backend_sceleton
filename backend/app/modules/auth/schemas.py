"""Pydantic schemas for authentication module."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ============================================================================
# Token Schemas
# ============================================================================


class TokenPair(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiration in seconds")


class TokenRefresh(BaseModel):
    """Request schema for refreshing tokens."""

    refresh_token: str


# ============================================================================
# Login Schemas
# ============================================================================


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    """Login response with tokens and user info."""

    tokens: TokenPair
    user: "UserResponse"


# ============================================================================
# User Schemas
# ============================================================================


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, max_length=100)
    role_id: UUID | None = None
    is_active: bool = True


class UserUpdate(BaseModel):
    """Schema for updating a user.
    
    Note: avatar_url is managed via POST/DELETE /auth/users/{id}/avatar endpoints.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None
    role_id: UUID | None = None
    version: int = Field(..., description="Current version for optimistic locking")


class PasswordChange(BaseModel):
    """Schema for changing password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=100)


class UserResponse(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    is_active: bool
    is_superuser: bool
    avatar_url: str | None = None
    last_login_at: datetime | None = None
    role: "RoleResponse | None" = None
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Schema for user list response."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Role Schemas
# ============================================================================


class RoleBase(BaseModel):
    """Base role schema."""

    name: str = Field(..., min_length=2, max_length=50)
    description: str | None = None


class RoleCreate(RoleBase):
    """Schema for creating a role."""

    permission_ids: list[UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    name: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = None
    permission_ids: list[UUID] | None = None


class RoleResponse(RoleBase):
    """Schema for role response."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    is_system: bool
    permissions: list["PermissionResponse"] = Field(
        default_factory=list,
        validation_alias="role_permissions"
    )
    created_at: datetime
    updated_at: datetime

    @field_validator("permissions", mode="before")
    @classmethod
    def extract_permissions(cls, v: Any) -> list[Any]:
        """Extract Permission objects from RolePermission list."""
        if v is None:
            return []
        # If it's a list of RolePermission objects, extract the permission
        if v and hasattr(v[0], "permission"):
            return [rp.permission for rp in v if rp.permission]
        return list(v) if v else []


class RoleListResponse(BaseModel):
    """Schema for role list response."""

    items: list[RoleResponse]
    total: int


# ============================================================================
# Permission Schemas
# ============================================================================


class PermissionResponse(BaseModel):
    """Schema for permission response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None = None
    resource: str
    action: str


class PermissionListResponse(BaseModel):
    """Schema for permission list response."""

    items: list[PermissionResponse]
    total: int


# ============================================================================
# Current User Schemas
# ============================================================================


class MeResponse(BaseModel):
    """Schema for current user info response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: str
    first_name: str
    last_name: str
    full_name: str
    avatar_url: str | None = None
    is_superuser: bool
    role: RoleResponse | None = None
    permissions: list[str] = Field(default_factory=list)


# Fix forward references
LoginResponse.model_rebuild()
UserResponse.model_rebuild()
RoleResponse.model_rebuild()

