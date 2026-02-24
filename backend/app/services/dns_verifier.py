"""DNS verification for custom tenant domains.

Checks whether a domain has a CNAME record pointing to the platform's
CNAME target (e.g. tenants.mediann.dev). Also supports A-record fallback
for apex domains that cannot use CNAME.
"""

import asyncio
import socket
from dataclasses import dataclass
from functools import partial

import dns.resolver

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DNSCheckResult:
    ok: bool
    cname_target: str | None
    expected_target: str
    message: str


def _resolve_cname(domain: str) -> list[str]:
    """Blocking DNS CNAME lookup (runs in thread pool)."""
    try:
        answers = dns.resolver.resolve(domain, "CNAME")
        return [str(rdata.target).rstrip(".") for rdata in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return []


def _resolve_a(domain: str) -> list[str]:
    """Blocking DNS A-record lookup (runs in thread pool)."""
    try:
        answers = dns.resolver.resolve(domain, "A")
        return [str(rdata.address) for rdata in answers]
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.DNSException):
        return []


def _resolve_server_ip(hostname: str) -> str | None:
    """Resolve the platform CNAME target to an IP for A-record comparison."""
    try:
        info = socket.getaddrinfo(hostname, None, socket.AF_INET)
        if info:
            return info[0][4][0]
    except socket.gaierror:
        pass
    return None


async def verify_domain_dns(domain: str) -> DNSCheckResult:
    """Verify that *domain* has correct DNS configuration.

    Checks:
    1. CNAME record pointing to ``platform_cname_target``
    2. Fallback: A-record matching the platform server IP
    """
    settings = get_settings()
    expected = settings.platform_cname_target.rstrip(".")
    loop = asyncio.get_running_loop()

    # 1. CNAME check
    cname_targets = await loop.run_in_executor(None, partial(_resolve_cname, domain))
    if cname_targets:
        for target in cname_targets:
            if target == expected:
                return DNSCheckResult(
                    ok=True,
                    cname_target=target,
                    expected_target=expected,
                    message="CNAME record configured correctly",
                )
        return DNSCheckResult(
            ok=False,
            cname_target=cname_targets[0] if cname_targets else None,
            expected_target=expected,
            message=f"CNAME points to {cname_targets[0]}, expected {expected}",
        )

    # 2. A-record fallback (for apex domains)
    a_records = await loop.run_in_executor(None, partial(_resolve_a, domain))
    if a_records:
        server_ip = await loop.run_in_executor(
            None, partial(_resolve_server_ip, expected)
        )
        if server_ip and server_ip in a_records:
            return DNSCheckResult(
                ok=True,
                cname_target=None,
                expected_target=expected,
                message=f"A-record resolves to {server_ip} (matches platform server)",
            )
        return DNSCheckResult(
            ok=False,
            cname_target=None,
            expected_target=expected,
            message=(
                f"A-record resolves to {', '.join(a_records)}, "
                f"expected CNAME to {expected}"
            ),
        )

    # 3. No DNS records at all
    logger.warning("dns_verify_no_records", domain=domain)
    return DNSCheckResult(
        ok=False,
        cname_target=None,
        expected_target=expected,
        message=(
            f"No CNAME or A record found for {domain}. "
            f"Add a CNAME record pointing to {expected}"
        ),
    )
