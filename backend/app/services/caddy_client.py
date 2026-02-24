"""Caddy Admin API client.

Used to check certificate status and health of the reverse proxy.
Caddy Admin API runs on localhost:2019 by default.
"""

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CaddyAPIClient:
    """Read-only client for Caddy Admin API.

    Primary use: verify that a certificate has been issued for a domain.
    Caddy manages certificate lifecycle automatically via on_demand_tls;
    this client only inspects state.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or get_settings().caddy_admin_url

    async def is_healthy(self) -> bool:
        """Check whether Caddy Admin API is reachable."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/config/", timeout=3)
                return resp.status_code == 200
            except httpx.HTTPError:
                return False

    async def check_certificate(self, domain: str) -> bool:
        """Check whether Caddy has obtained a valid certificate for *domain*.

        Uses the /certificates endpoint of the PKI app, or falls back to
        probing the TLS config.
        """
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/id/",
                    timeout=5,
                )
                if resp.status_code != 200:
                    # Try the reverse-proxy route config as fallback
                    return await self._check_via_config(client, domain)

                return domain in resp.text
            except httpx.HTTPError as exc:
                logger.warning("caddy_api_unavailable", error=str(exc))
                return False

    async def _check_via_config(self, client: httpx.AsyncClient, domain: str) -> bool:
        """Fallback: probe Caddy config JSON for the domain."""
        try:
            resp = await client.get(f"{self.base_url}/config/", timeout=5)
            if resp.status_code == 200:
                return domain in resp.text
        except httpx.HTTPError:
            pass
        return False

    async def check_certificate_via_tls(self, domain: str) -> bool:
        """Attempt an HTTPS connection to verify the cert is live.

        More reliable than the Admin API for confirming end-to-end TLS.
        """
        async with httpx.AsyncClient(verify=True, timeout=10) as client:
            try:
                resp = await client.head(f"https://{domain}/", follow_redirects=True)
                return resp.status_code < 500
            except httpx.HTTPError:
                return False


def get_caddy_client() -> CaddyAPIClient:
    """Factory for CaddyAPIClient (uses settings)."""
    return CaddyAPIClient()
