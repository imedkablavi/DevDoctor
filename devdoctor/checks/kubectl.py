"""kubectl tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_kubectl() -> CheckResult:
    """Check kubectl availability."""

    return check_tool(
        ToolDefinition(
            id="tool.kubectl",
            title="kubectl",
            executable="kubectl",
            version_args=("version", "--client=true"),
            install_hint="Install kubectl if you work with Kubernetes clusters.",
            weight=1,
            timeout=6,
        )
    )
