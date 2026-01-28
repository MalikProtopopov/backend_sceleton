"""API routes for company module.

This module includes sub-routers for each company entity:
- service_router: Services (public + admin + locales + prices + tags)
- employee_router: Employees (public + admin + locales)
- other_router: Practice areas, advantages, contacts, addresses
"""

from fastapi import APIRouter

from app.modules.company.routers import (
    employee_router,
    other_router,
    service_router,
)

router = APIRouter()

# Include all sub-routers
router.include_router(service_router)
router.include_router(employee_router)
router.include_router(other_router)
