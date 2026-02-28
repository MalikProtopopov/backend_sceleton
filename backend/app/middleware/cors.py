"""Dynamic CORS middleware with database-backed origin checking.

Replaces the standard Starlette ``CORSMiddleware`` so that allowed
origins are loaded from the database (tenant domains + site URLs)
combined with a static fallback list from the ``CORS_ORIGINS`` env var.
"""

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger
from app.core.redis import get_cors_origins_cache

logger = get_logger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PREFLIGHT_MAX_AGE = "86400"

CORS_HEADERS = {
    "access-control-allow-credentials": "true",
    "access-control-allow-methods": "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS",
    "access-control-allow-headers": "Content-Type, Authorization, X-Tenant-ID, X-Requested-With, Accept, Accept-Language",
    "access-control-max-age": PREFLIGHT_MAX_AGE,
    "vary": "Origin",
}


class DynamicCORSMiddleware:
    """ASGI middleware that checks the ``Origin`` header against a
    dynamically-loaded set of allowed origins.

    The origin list is managed by :class:`~app.core.redis.CORSOriginsCache`
    which combines ``.env`` fallback origins with domains pulled from the
    ``tenant_domains`` and ``tenant_settings`` tables.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        origin = request.headers.get("origin")

        if not origin:
            await self.app(scope, receive, send)
            return

        cache = get_cors_origins_cache()
        allowed_origins = await cache.get_allowed_origins()
        origin_normalized = origin.rstrip("/")
        is_allowed = origin_normalized in allowed_origins

        if request.method == "OPTIONS" and "access-control-request-method" in request.headers:
            response = self._preflight_response(origin, is_allowed)
            await response(scope, receive, send)
            return

        await self._simple_response(scope, receive, send, origin, is_allowed)

    def _preflight_response(self, origin: str, is_allowed: bool) -> Response:
        if not is_allowed:
            return PlainTextResponse("Disallowed CORS origin", status_code=400)

        headers = {
            "access-control-allow-origin": origin,
            **CORS_HEADERS,
        }
        return PlainTextResponse("OK", status_code=200, headers=headers)

    async def _simple_response(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        origin: str,
        is_allowed: bool,
    ) -> None:
        headers_to_add: list[tuple[bytes, bytes]] = []
        if is_allowed:
            headers_to_add = [
                (b"access-control-allow-origin", origin.encode()),
                (b"access-control-allow-credentials", b"true"),
                (b"vary", b"Origin"),
            ]

        async def send_with_cors(message: Message) -> None:
            if message["type"] == "http.response.start" and headers_to_add:
                headers = MutableHeaders(scope=message)
                for key, value in headers_to_add:
                    headers.append(key.decode(), value.decode())
            await send(message)

        await self.app(scope, receive, send_with_cors)
