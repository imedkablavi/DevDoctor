"""Bun tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_bun() -> CheckResult:
    """Check Bun availability."""

    return check_tool(
        ToolDefinition(
            id="tool.bun",
            title="Bun",
            executable="bun",
            install_hint="Install Bun from https://bun.sh when your projects depend on it.",
            weight=1,
        )
    )
