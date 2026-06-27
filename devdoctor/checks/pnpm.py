"""pnpm tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_pnpm() -> CheckResult:
    """Check pnpm availability."""

    return check_tool(
        ToolDefinition(
            id="tool.pnpm",
            title="pnpm",
            executable="pnpm",
            install_hint="Install pnpm with Corepack (`corepack enable`) or your package manager.",
            weight=1,
        )
    )
