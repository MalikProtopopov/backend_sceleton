"""Feature flag checking middleware.

Provides dependency functions for checking if features/modules are enabled
before allowing access to related endpoints.

Two variants:
- require_feature() -- for admin routes (requires authentication token)
- require_feature_public() -- for public routes (uses tenant_id from query param)
"""

from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_public_tenant_id
from app.core.exceptions import FeatureDisabledError, FeatureNotAvailableError
from app.core.security import TokenPayload, get_current_token
from app.modules.tenants.service import FeatureFlagService


def require_feature(feature_name: str):
    """Create a dependency that checks if a feature is enabled (admin routes).
    
    This dependency can be added to route handlers to ensure
    the requested feature/module is enabled for the current tenant.
    
    Superusers and platform_owners always have access regardless
    of feature flag status.
    
    Args:
        feature_name: Name of the feature to check (e.g., "cases_module")
        
    Returns:
        A FastAPI dependency function
        
    Usage:
        @router.get("/admin/cases", dependencies=[require_cases])
        async def list_cases(...):
            ...
    """
    
    async def dependency(
        token: TokenPayload = Depends(get_current_token),
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        """Check if feature is enabled for current tenant."""
        # Superusers always have access to all features
        if token.is_superuser:
            return True
        
        # Check if user has platform_owner role (from permissions)
        if "platform:*" in token.permissions or "platform:update" in token.permissions:
            return True
        
        # Check feature flag in database
        service = FeatureFlagService(db)
        is_enabled = await service.is_enabled(token.tenant_id, feature_name)
        
        if not is_enabled:
            raise FeatureDisabledError(feature_name)
        
        return True
    
    return Depends(dependency)


def require_feature_public(feature_name: str):
    """Create a dependency that checks if a feature is enabled (public routes).
    
    Unlike require_feature(), this does NOT require authentication.
    It resolves tenant_id from the public query parameter and checks
    the feature flag directly. Returns 404 (not 403) to hide feature
    existence from public users.
    
    Args:
        feature_name: Name of the feature to check (e.g., "blog_module")
        
    Returns:
        A FastAPI dependency function
        
    Usage:
        @router.get("/public/articles", dependencies=[require_blog_public])
        async def list_articles_public(...):
            ...
    """
    
    async def dependency(
        tenant_id: UUID = Depends(get_public_tenant_id),
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        """Check if feature is enabled for the public tenant."""
        service = FeatureFlagService(db)
        is_enabled = await service.is_enabled(tenant_id, feature_name)
        
        if not is_enabled:
            raise FeatureNotAvailableError(feature_name)
        
        return True
    
    return Depends(dependency)


class FeatureRequiredChecker:
    """Class-based dependency for feature checking.
    
    Alternative to require_feature() function that can be used
    when you need more control over the dependency.
    
    Usage:
        cases_feature = FeatureRequiredChecker("cases_module")
        
        @router.get("/cases")
        async def list_cases(
            _: bool = Depends(cases_feature),
            ...
        ):
            ...
    """
    
    def __init__(self, feature_name: str):
        self.feature_name = feature_name
    
    async def __call__(
        self,
        token: TokenPayload = Depends(get_current_token),
        db: AsyncSession = Depends(get_db),
    ) -> bool:
        """Check if feature is enabled."""
        # Superusers always have access
        if token.is_superuser:
            return True
        
        # Check feature flag
        service = FeatureFlagService(db)
        is_enabled = await service.is_enabled(token.tenant_id, self.feature_name)
        
        if not is_enabled:
            raise FeatureDisabledError(self.feature_name)
        
        return True


# ============================================================================
# Pre-defined feature checkers for ADMIN routes (require auth)
# ============================================================================
require_blog = require_feature("blog_module")
require_cases = require_feature("cases_module")
require_reviews = require_feature("reviews_module")
require_faq = require_feature("faq_module")
require_team = require_feature("team_module")
require_services = require_feature("services_module")
require_seo_advanced = require_feature("seo_advanced")
require_multilang = require_feature("multilang")
require_analytics_advanced = require_feature("analytics_advanced")

# ============================================================================
# Pre-defined feature checkers for PUBLIC routes (no auth needed)
# ============================================================================
require_blog_public = require_feature_public("blog_module")
require_cases_public = require_feature_public("cases_module")
require_reviews_public = require_feature_public("reviews_module")
require_faq_public = require_feature_public("faq_module")
require_team_public = require_feature_public("team_module")
require_services_public = require_feature_public("services_module")

