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
    send_credentials: bool = Field(
        default=True,
        description="Send welcome email to the new user with login URL and account info",
    )


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
    force_password_change: bool = False
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
    force_password_change: bool = False
    role: RoleResponse | None = None
    permissions: list[str] = Field(default_factory=list)


class EnabledFeaturesResponse(BaseModel):
    """Schema for enabled features response (legacy).
    
    Used by frontend to determine which sections to show in sidebar.
    Kept for backward compatibility; prefer FeatureCatalogResponse.
    """
    
    enabled_features: list[str] = Field(
        default_factory=list,
        description="List of enabled feature names for this tenant"
    )
    all_features_enabled: bool = Field(
        default=False,
        description="True if user is superuser/platform_owner (has access to all features)"
    )


class FeatureCatalogItem(BaseModel):
    """Single feature in the catalog."""

    name: str = Field(..., description="Feature key (e.g. 'blog_module')")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Feature description")
    category: str = Field(..., description="Feature category (content, company, platform)")
    enabled: bool = Field(..., description="Whether this feature is enabled for the tenant")
    can_request: bool = Field(
        ...,
        description="Whether the user can request enabling this feature (true when disabled)",
    )


class FeatureCatalogResponse(BaseModel):
    """Full feature catalog with per-feature details.
    
    Used by frontend to build sidebar showing available, disabled,
    and requestable sections in one API call.
    """

    features: list[FeatureCatalogItem] = Field(
        default_factory=list,
        description="Full catalog of all platform features with their status",
    )
    all_features_enabled: bool = Field(
        default=False,
        description="True if user is superuser/platform_owner (has access to all features)",
    )
    tenant_id: UUID = Field(..., description="Tenant ID for this catalog")


# ============================================================================
# Tenant Switcher Schemas
# ============================================================================


class TenantAccessInfo(BaseModel):
    """Summary of a single tenant the user has access to."""

    tenant_id: UUID
    name: str
    slug: str
    logo_url: str | None = None
    primary_color: str | None = None
    admin_domain: str | None = Field(
        default=None,
        description="Primary admin-panel domain for this tenant (e.g. admin.client.com)",
    )


class MyTenantsResponse(BaseModel):
    """Response for GET /auth/me/tenants."""

    current_tenant_id: UUID
    tenants: list[TenantAccessInfo]


class SwitchTenantRequest(BaseModel):
    """Request body for POST /auth/switch-tenant."""

    tenant_id: UUID


# ============================================================================
# Password Reset Schemas
# ============================================================================


class ForgotPasswordRequest(BaseModel):
    """Request schema for forgot password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request schema for resetting password with token."""

    token: str = Field(..., min_length=1, description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


# Fix forward references
LoginResponse.model_rebuild()
UserResponse.model_rebuild()
RoleResponse.model_rebuild()

