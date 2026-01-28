"""Company module sub-routers."""

from app.modules.company.routers.service_router import router as service_router
from app.modules.company.routers.employee_router import router as employee_router
from app.modules.company.routers.other_router import router as other_router

__all__ = [
    "service_router",
    "employee_router",
    "other_router",
]
