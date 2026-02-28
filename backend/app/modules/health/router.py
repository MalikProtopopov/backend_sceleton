"""Health check endpoints."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.core.database import check_db_connection
from app.core.redis import check_redis_connection

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response with dependency status."""

    status: str
    checks: dict[str, bool]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Returns OK if the service is running. Use for load balancer health checks.",
)
async def health() -> HealthResponse:
    """Basic health check - always returns OK if service is running."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
    )


@router.get(
    "/health/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Kubernetes liveness probe. Returns OK if the application is alive.",
)
async def liveness() -> HealthResponse:
    """Liveness probe for Kubernetes."""
    return HealthResponse(
        status="ok",
        version=settings.app_version,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Kubernetes readiness probe. Checks all dependencies (database, redis).",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Service not ready - one or more dependencies are down",
        }
    },
)
async def readiness():
    """Readiness probe - checks all dependencies.

    Returns 200 when all services are healthy, 503 otherwise.
    """
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()

    all_ok = db_ok and redis_ok
    body = ReadinessResponse(
        status="ok" if all_ok else "degraded",
        checks={"database": db_ok, "redis": redis_ok},
    )

    if not all_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=body.model_dump(),
        )
    return body

