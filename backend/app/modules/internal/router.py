"""Internal API endpoints (localhost only).

These endpoints are called by infrastructure services (e.g. Caddy)
and must NOT be exposed to the public internet.
"""

import hmac

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError
from app.core.logging import get_logger
from app.modules.tenants.models import TenantDomain

logger = get_logger(__name__)
router = APIRouter()

_LOCALHOST_IPS = {"127.0.0.1", "::1"}


def _is_internal_ip(ip: str) -> bool:
    return (
        ip in _LOCALHOST_IPS
        or ip.startswith("172.")
        or ip.startswith("10.")
        or ip.startswith("192.168.")
    )


@router.get(
    "/domains/check",
    summary="Caddy on_demand_tls arbiter",
    description=(
        "Called by Caddy before issuing a TLS certificate for an unknown domain. "
        "Returns 200 if the domain is allowed, 403 otherwise. "
        "Only accessible from localhost."
    ),
    responses={
        200: {"description": "Domain allowed — Caddy may issue certificate"},
        403: {"description": "Domain denied — Caddy must NOT issue certificate"},
    },
)
async def check_domain_for_caddy(
    request: Request,
    domain: str = Query(..., description="Hostname to check"),
    x_internal_secret: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Caddy calls this before issuing a cert via on_demand_tls.

    Security: requires a shared secret header (INTERNAL_SECRET env var)
    or a request from a private IP address (Docker network).
    """
    settings = get_settings()
    internal_secret = getattr(settings, "internal_secret", "")
    client_host = request.client.host if request.client else ""

    secret_ok = (
        bool(internal_secret)
        and bool(x_internal_secret)
        and hmac.compare_digest(x_internal_secret, internal_secret)
    )

    if not secret_ok and not _is_internal_ip(client_host):
        logger.warning(
            "internal_check_rejected",
            client_host=client_host,
            domain=domain,
        )
        raise PermissionDeniedError(message="Internal only")

    settings = get_settings()
    domain_lower = domain.strip().lower()

    # Platform subdomains are always allowed (covered by wildcard cert,
    # but Caddy may still ask in edge cases)
    if domain_lower.endswith(settings.platform_domain_suffix):
        return Response(status_code=200)

    # Custom domains: check the database
    result = await db.execute(
        select(TenantDomain.id).where(
            TenantDomain.domain == domain_lower,
            TenantDomain.ssl_status.in_(["pending", "verifying", "active"]),
        )
    )
    if result.scalar_one_or_none() is not None:
        logger.info("caddy_domain_approved", domain=domain_lower)
        return Response(status_code=200)

    logger.info("caddy_domain_denied", domain=domain_lower)
    raise PermissionDeniedError(message="Domain not registered")
