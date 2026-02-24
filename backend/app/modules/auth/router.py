"""Auth module router aggregator."""

from fastapi import APIRouter

from app.modules.auth.routers import auth_router, user_router, role_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(user_router)
router.include_router(role_router)
