"""Request logging middleware for tracking all API requests."""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)

# Sensitive parameter names that should be filtered from logs
SENSITIVE_PARAMS = frozenset({
    "password",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "secret",
    "authorization",
    "auth",
    "access_token",
    "refresh_token",
    "jwt",
    "bearer",
    "credential",
    "credentials",
    "private_key",
    "privatekey",
})


def _filter_sensitive_params(query_params: str) -> str:
    """Filter sensitive parameters from query string for safe logging.
    
    Args:
        query_params: Query parameters as string (e.g., "foo=bar&token=secret")
        
    Returns:
        Filtered query params with sensitive values redacted
    """
    if not query_params:
        return query_params
    
    # Parse and filter each parameter
    filtered_parts = []
    for part in query_params.split("&"):
        if "=" in part:
            key, _ = part.split("=", 1)
            # Check if key (lowercase) matches any sensitive param
            if key.lower() in SENSITIVE_PARAMS:
                filtered_parts.append(f"{key}=[REDACTED]")
            else:
                filtered_parts.append(part)
        else:
            filtered_parts.append(part)
    
    return "&".join(filtered_parts)


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

        # Log request start with filtered query params (security: hide sensitive data)
        filtered_params = _filter_sensitive_params(str(request.query_params))
        logger.info(
            "request_started",
            query_params=filtered_params,
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

