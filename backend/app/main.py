"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.database import check_db_connection, close_db
from app.core.exceptions import AppException
from app.core.logging import get_logger, setup_logging
from app.core.redis import check_redis_connection, close_redis, init_redis
from app.middleware.cache import CacheHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware

# Setup logging on module load
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Check database connection
    if await check_db_connection():
        logger.info("database_connected")
    else:
        logger.error("database_connection_failed")

    # Initialize Redis
    try:
        await init_redis()
    except Exception as e:
        logger.warning("redis_init_failed", error=str(e))

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await close_redis()
    await close_db()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Reusable backend engine for corporate websites",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Register middleware
    _setup_middleware(app)

    # Register exception handlers
    _setup_exception_handlers(app)

    # Register routers
    _setup_routers(app)

    return app


def _setup_middleware(app: FastAPI) -> None:
    """Configure application middleware."""
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Cache headers (runs last on response, adds Cache-Control and ETag)
    app.add_middleware(CacheHeadersMiddleware)

    # Rate limiting (must be before request logging)
    app.add_middleware(RateLimitMiddleware)

    # Request logging (runs first, logs all requests)
    app.add_middleware(RequestLoggingMiddleware)


def _setup_exception_handlers(app: FastAPI) -> None:
    """Configure global exception handlers."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle AppException with RFC 7807 format."""
        # Add request path to error detail
        error_detail = exc.detail
        if isinstance(error_detail, dict):
            error_detail["instance"] = str(request.url.path)

        return JSONResponse(
            status_code=exc.status_code,
            content=error_detail,
            headers={"Content-Type": "application/problem+json"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception("unhandled_exception", error=str(exc), path=request.url.path)

        return JSONResponse(
            status_code=500,
            content={
                "type": "https://api.cms.local/errors/internal_error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred" if settings.is_production else str(exc),
                "instance": str(request.url.path),
            },
            headers={"Content-Type": "application/problem+json"},
        )


def _setup_routers(app: FastAPI) -> None:
    """Register API routers."""
    from app.modules.assets.router import media_router, router as assets_router
    from app.modules.audit.router import router as audit_router
    from app.modules.auth.router import router as auth_router
    from app.modules.company.router import router as company_router
    from app.modules.content.router import router as content_router
    from app.modules.dashboard.router import router as dashboard_router
    from app.modules.documents.router import router as documents_router
    from app.modules.export.router import router as export_router
    from app.modules.health.router import router as health_router
    from app.modules.leads.router import router as leads_router
    from app.modules.seo.router import router as seo_router
    from app.modules.telegram.router import router as telegram_router
    from app.modules.tenants.router import router as tenants_router

    # Health checks (no prefix)
    app.include_router(health_router, tags=["Health"])

    # API v1 routes
    app.include_router(
        auth_router,
        prefix=f"{settings.api_prefix}/auth",
        tags=["Authentication"],
    )
    
    # Backward compatibility: also register auth routes without /api/v1 prefix
    # This allows frontend to use /auth/login instead of /api/v1/auth/login
    app.include_router(
        auth_router,
        prefix="/auth",
        tags=["Authentication"],
    )
    app.include_router(
        tenants_router,
        prefix=settings.api_prefix,
        tags=["Tenants & Feature Flags"],
    )
    app.include_router(
        dashboard_router,
        prefix=f"{settings.api_prefix}/admin",
        tags=["Dashboard"],
    )
    app.include_router(
        audit_router,
        prefix=f"{settings.api_prefix}/admin",
        tags=["Audit"],
    )
    app.include_router(
        export_router,
        prefix=f"{settings.api_prefix}/admin",
        tags=["Export"],
    )
    app.include_router(
        company_router,
        prefix=settings.api_prefix,
        tags=["Company"],
    )
    app.include_router(
        content_router,
        prefix=settings.api_prefix,
        tags=["Content"],
    )
    app.include_router(
        documents_router,
        prefix=settings.api_prefix,
        tags=["Documents"],
    )
    app.include_router(
        leads_router,
        prefix=settings.api_prefix,
        tags=["Leads"],
    )
    app.include_router(
        seo_router,
        prefix=settings.api_prefix,
        tags=["SEO"],
    )
    app.include_router(
        assets_router,
        prefix=settings.api_prefix,
        tags=["Assets"],
    )
    app.include_router(
        telegram_router,
        prefix=settings.api_prefix,
        tags=["Telegram"],
    )

    # Public media endpoint (without API prefix)
    app.include_router(
        media_router,
        prefix="/media",
        tags=["Media"],
    )


# Create app instance
app = create_app()

