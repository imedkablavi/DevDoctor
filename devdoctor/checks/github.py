"""GitHub CLI and reachability checks."""

from __future__ import annotations

import socket

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import measure_tcp_latency


def check_github_cli() -> CheckResult:
    """Check GitHub CLI availability."""

    return check_tool(
        ToolDefinition(
            id="tool.github_cli",
            title="GitHub CLI",
            executable="gh",
            install_hint=(
                "Install the GitHub CLI from https://cli.github.com or your package manager."
            ),
            weight=1,
        )
    )


def check_github_reachability(timeout: float = 3.0) -> CheckResult:
    """Check GitHub DNS and HTTPS reachability."""

    host = "github.com"
    try:
        address = socket.gethostbyname(host)
    except OSError as exc:
        return CheckResult.failure(
            id="network.github",
            title="GitHub Reachability",
            category=CheckCategory.NETWORK,
            summary="GitHub DNS lookup failed.",
            details={"host": host, "error": str(exc)},
            recommendation=(
                "Fix DNS resolution before cloning repositories or using "
                "GitHub-hosted package sources."
            ),
            weight=4,
        )

    latency = measure_tcp_latency(host, 443, timeout)
    details = {"host": host, "address": address, "port": 443, "latency_ms": latency}
    if latency is None:
        return CheckResult.failure(
            id="network.github",
            title="GitHub Reachability",
            category=CheckCategory.NETWORK,
            summary="GitHub is not reachable over HTTPS.",
            details=details,
            recommendation=(
                "Check proxy, VPN, firewall, or captive portal settings for HTTPS access to GitHub."
            ),
            weight=4,
        )

    return CheckResult.ok(
        id="network.github",
        title="GitHub Reachability",
        category=CheckCategory.NETWORK,
        summary=f"GitHub HTTPS reachable in {latency:.0f} ms.",
        details=details,
        weight=3,
    )
