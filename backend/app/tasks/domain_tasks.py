"""Background tasks for domain SSL provisioning.

These tasks are enqueued when a custom domain is added or when
DNS verification is requested.
"""

import asyncio
from uuid import UUID

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.services.domain_provisioning import DomainProvisioningService
from app.tasks.broker import broker

# Import all models so SQLAlchemy can resolve cross-module relationships
# (e.g. Tenant.relationship("AdminUser")) before mappers are configured.
import app.modules.auth.models  # noqa: F401
import app.modules.tenants.models  # noqa: F401
import app.modules.company.models  # noqa: F401
import app.modules.documents.models  # noqa: F401
import app.modules.leads.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.content.models  # noqa: F401
import app.modules.assets.models  # noqa: F401
import app.modules.catalog.models  # noqa: F401
import app.modules.parameters.models  # noqa: F401
import app.modules.variants.models  # noqa: F401
import app.modules.seo.models  # noqa: F401
import app.modules.audit.models  # noqa: F401
import app.modules.telegram.models  # noqa: F401
import app.modules.localization.models  # noqa: F401

logger = get_logger(__name__)

_MAX_POLL_ATTEMPTS = 10
_POLL_INTERVAL_SEC = 30


@broker.task(retry_on_error=True, max_retries=3)
async def provision_domain_task(domain_id: str) -> dict:
    """Full provisioning: DNS check + trigger Caddy cert issuance.

    Enqueued by TenantDomainService.add_domain() and by the
    POST /verify endpoint.
    """
    logger.info("task_provision_domain_start", domain_id=domain_id)
    async with get_db_context() as db:
        service = DomainProvisioningService(db)
        await service.provision_domain(UUID(domain_id))
        await db.commit()

    # Schedule SSL status polling after a short delay
    await asyncio.sleep(5)
    await poll_ssl_status_task.kiq(domain_id, 0)
    return {"status": "provisioning_started", "domain_id": domain_id}


@broker.task(retry_on_error=True, max_retries=1)
async def poll_ssl_status_task(domain_id: str, attempt: int = 0) -> dict:
    """Poll Caddy to check if the certificate has been issued.

    Re-enqueues itself up to ``_MAX_POLL_ATTEMPTS`` times until status
    becomes 'active' or 'error'.
    """
    logger.info(
        "task_poll_ssl_status",
        domain_id=domain_id,
        attempt=attempt,
    )

    async with get_db_context() as db:
        service = DomainProvisioningService(db)
        status = await service.check_and_update_ssl_status(UUID(domain_id))
        await db.commit()

    if status in ("active", "error"):
        logger.info("task_poll_ssl_done", domain_id=domain_id, status=status)
        return {"status": status, "domain_id": domain_id}

    if attempt >= _MAX_POLL_ATTEMPTS:
        logger.warning("task_poll_ssl_max_attempts", domain_id=domain_id)
        # Mark as error after exhausting retries
        async with get_db_context() as db:
            from sqlalchemy import update

            from app.modules.tenants.models import TenantDomain

            await db.execute(
                update(TenantDomain)
                .where(TenantDomain.id == UUID(domain_id))
                .values(ssl_status="error")
            )
            await db.commit()
        return {"status": "error", "domain_id": domain_id, "reason": "max_attempts"}

    # Re-schedule after delay
    await asyncio.sleep(_POLL_INTERVAL_SEC)
    await poll_ssl_status_task.kiq(domain_id, attempt + 1)
    return {"status": "polling", "domain_id": domain_id, "attempt": attempt}
