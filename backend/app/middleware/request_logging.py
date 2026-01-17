"""Request logging middleware for tracking all API requests."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests with timing and context.

    Adds request_id to all log messages during request processing.
    Logs request start and completion with timing information.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Bind context for all log messages in this request
        bind_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=self._get_client_ip(request),
        )

        # Add request_id to response headers
        start_time = time.perf_counter()

        # Log request start
        logger.info(
            "request_started",
            query_params=str(request.query_params),
            user_agent=request.headers.get("user-agent", ""),
        )

        try:
            response = await call_next(request)

            # Calculate processing time
            process_time = time.perf_counter() - start_time

            # Log request completion
            logger.info(
                "request_completed",
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )

            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f}"

            return response

        except Exception as exc:
            process_time = time.perf_counter() - start_time
            logger.exception(
                "request_failed",
                error=str(exc),
                process_time_ms=round(process_time * 1000, 2),
            )
            raise

        finally:
            # Clear context at end of request
            clear_context()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check for forwarded headers (when behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"

