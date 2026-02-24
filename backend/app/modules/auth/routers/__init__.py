"""Auth module sub-routers."""

from app.modules.auth.routers.auth_router import router as auth_router
from app.modules.auth.routers.user_router import router as user_router
from app.modules.auth.routers.role_router import router as role_router

__all__ = [
    "auth_router",
    "user_router",
    "role_router",
]
