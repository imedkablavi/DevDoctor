"""DNS resolution checks."""

from __future__ import annotations

import socket
import time

from devdoctor.models import CheckCategory, CheckResult


def check_dns(timeout: float = 3.0) -> CheckResult:
    """Check DNS resolution for developer-critical hosts."""

    previous_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    hosts = ("github.com", "pypi.org", "registry.npmjs.org")
    resolved: dict[str, str] = {}
    errors: dict[str, str] = {}
    started_at = time.perf_counter()
    try:
        for host in hosts:
            try:
                resolved[host] = socket.gethostbyname(host)
            except OSError as exc:
                errors[host] = str(exc)
    finally:
        socket.setdefaulttimeout(previous_timeout)

    elapsed_ms = (time.perf_counter() - started_at) * 1000
    details = {
        "resolved": resolved,
        "errors": errors,
        "latency_ms": round(elapsed_ms, 1),
    }
    if not errors:
        return CheckResult.ok(
            id="network.dns",
            title="DNS Resolution",
            category=CheckCategory.NETWORK,
            summary=f"DNS resolved {len(resolved)} developer hosts in {elapsed_ms:.0f} ms.",
            details=details,
            weight=4,
        )
    if resolved:
        return CheckResult.warning(
            id="network.dns",
            title="DNS Resolution",
            category=CheckCategory.NETWORK,
            summary=f"DNS resolved {len(resolved)} of {len(hosts)} developer hosts.",
            details=details,
            recommendation="Check DNS configuration if package installs intermittently fail.",
            weight=2,
        )
    return CheckResult.failure(
        id="network.dns",
        title="DNS Resolution",
        category=CheckCategory.NETWORK,
        summary="DNS resolution failed for all developer hosts.",
        details=details,
        recommendation="Fix DNS servers in NetworkManager, systemd-resolved, or your VPN profile.",
        weight=5,
    )
