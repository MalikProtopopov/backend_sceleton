"""Domain provisioning orchestrator.

Coordinates DNS verification, SSL certificate issuance via Caddy,
and status updates in the database.
"""

from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import transactional
from app.core.logging import get_logger
from app.modules.tenants.models import TenantDomain
from app.modules.tenants.services.caddy_client import get_caddy_client
from app.modules.tenants.services.dns_verifier import verify_domain_dns

logger = get_logger(__name__)


class DomainProvisioningService:
    """Orchestrates the full domain provisioning lifecycle.

    Flow:
        1. Verify DNS (CNAME → tenants.mediann.dev)
        2. Set status to 'verifying'
        3. Trigger Caddy to issue cert (HTTPS probe)
        4. Poll / check that cert was issued
        5. Set status to 'active' or 'error'
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.caddy = get_caddy_client()

    async def provision_domain(self, domain_id: UUID) -> None:
        """Full provisioning: DNS check → trigger cert → update status."""
        td = await self._get_domain(domain_id)
        if td is None:
            logger.error("provision_domain_not_found", domain_id=str(domain_id))
            return

        logger.info("provision_domain_start", domain=td.domain, domain_id=str(domain_id))

        # 1. DNS verification
        dns_result = await verify_domain_dns(td.domain)
        if not dns_result.ok:
            await self._update_status(td, "error")
            logger.warning(
                "provision_dns_failed",
                domain=td.domain,
                message=dns_result.message,
            )
            return

        # 2. Mark as verifying + record DNS verification time
        td.dns_verified_at = datetime.now(timezone.utc)
        await self._update_status(td, "verifying")

        # 3. Trigger Caddy cert issuance via HTTPS probe
        cert_ok = await self._trigger_and_verify_cert(td.domain)
        if cert_ok:
            td.ssl_provisioned_at = datetime.now(timezone.utc)
            await self._update_status(td, "active")
            logger.info("provision_domain_success", domain=td.domain)
        else:
            # Leave as 'verifying' — poll_ssl_status_task will retry
            logger.info("provision_cert_pending", domain=td.domain)

    async def check_and_update_ssl_status(self, domain_id: UUID) -> str:
        """Check current cert status and update DB accordingly.

        Called by the polling task after provisioning.
        """
        td = await self._get_domain(domain_id)
        if td is None:
            return "error"

        if td.ssl_status == "active":
            return "active"

        cert_ok = await self.caddy.check_certificate_via_tls(td.domain)
        if cert_ok:
            td.ssl_provisioned_at = datetime.now(timezone.utc)
            await self._update_status(td, "active")
            logger.info("ssl_status_now_active", domain=td.domain)
        return td.ssl_status

    @transactional
    async def verify_dns_only(self, domain_id: UUID) -> dict:
        """Run DNS check without triggering cert issuance.

        Returns a dict suitable for DNSVerifyResponse.
        """
        td = await self._get_domain(domain_id)
        if td is None:
            return {
                "ok": False,
                "cname_target": None,
                "expected_target": "",
                "message": "Domain not found",
            }

        result = await verify_domain_dns(td.domain)
        if result.ok:
            td.dns_verified_at = datetime.now(timezone.utc)
            await self.db.flush()

        return {
            "ok": result.ok,
            "cname_target": result.cname_target,
            "expected_target": result.expected_target,
            "message": result.message,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _trigger_and_verify_cert(self, domain: str) -> bool:
        """Make an HTTPS request to the domain, triggering Caddy's on_demand_tls.

        Caddy will see the incoming TLS handshake, call the ``ask`` endpoint,
        get 200, and start ACME certificate issuance.
        Returns True if the cert is immediately available.
        """
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            try:
                resp = await client.get(
                    f"https://{domain}/",
                    follow_redirects=True,
                )
                # If we get any response at all, TLS handshake succeeded
                return resp.status_code < 500
            except httpx.ConnectError:
                logger.debug("cert_trigger_connect_error", domain=domain)
                return False
            except Exception as exc:
                logger.debug("cert_trigger_exception", domain=domain, error=str(exc))
                return False

    async def _get_domain(self, domain_id: UUID) -> TenantDomain | None:
        result = await self.db.execute(
            select(TenantDomain).where(TenantDomain.id == domain_id)
        )
        return result.scalar_one_or_none()

    async def _update_status(self, td: TenantDomain, status: str) -> None:
        td.ssl_status = status
        await self.db.flush()
        logger.info(
            "domain_ssl_status_updated",
            domain=td.domain,
            ssl_status=status,
        )
