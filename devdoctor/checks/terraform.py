"""Terraform tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_terraform() -> CheckResult:
    """Check Terraform availability."""

    return check_tool(
        ToolDefinition(
            id="tool.terraform",
            title="Terraform",
            executable="terraform",
            install_hint="Install Terraform or OpenTofu if you manage infrastructure as code.",
            weight=1,
        )
    )
