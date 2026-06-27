"""Helm tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_helm() -> CheckResult:
    """Check Helm availability."""

    return check_tool(
        ToolDefinition(
            id="tool.helm",
            title="Helm",
            executable="helm",
            install_hint="Install Helm if you manage Kubernetes charts.",
            weight=1,
        )
    )
