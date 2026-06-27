"""Internet connectivity checks."""

from __future__ import annotations

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import measure_tcp_latency


def check_internet(timeout: float = 3.0) -> CheckResult:
    """Check outbound internet connectivity with TCP probes."""

    probes = (("1.1.1.1", 443), ("8.8.8.8", 53))
    probe_results: list[dict[str, object]] = []
    for host, port in probes:
        latency = measure_tcp_latency(host, port, timeout)
        probe_results.append({"host": host, "port": port, "latency_ms": latency})
        if latency is not None:
            return CheckResult.ok(
                id="network.internet",
                title="Internet Connectivity",
                category=CheckCategory.NETWORK,
                summary=f"Outbound connectivity works in {latency:.0f} ms.",
                details={"probes": probe_results},
                weight=5,
            )

    return CheckResult.failure(
        id="network.internet",
        title="Internet Connectivity",
        category=CheckCategory.NETWORK,
        summary="No outbound internet connectivity detected.",
        details={"probes": probe_results},
        recommendation="Check Wi-Fi, Ethernet, VPN, proxy, or firewall settings.",
        weight=5,
    )
