"""Structured JSON logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application.

    Uses JSON format in production, colored console output in development.
    """
    # Shared processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "json":
        # Production: JSON format for log aggregation
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: Colored console output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.database_echo else logging.WARNING
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Usage:
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        logger.info("user_created", user_id=user.id, email=user.email)
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to all subsequent log messages.

    Useful for adding request-scoped context like request_id, tenant_id.

    Usage:
        bind_context(request_id=request_id, tenant_id=tenant_id)
        logger.info("processing_request")  # Includes request_id and tenant_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all context variables.

    Call at the end of request processing.
    """
    structlog.contextvars.clear_contextvars()


def unbind_context(*keys: str) -> None:
    """Remove specific keys from context."""
    structlog.contextvars.unbind_contextvars(*keys)

