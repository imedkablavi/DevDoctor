"""npm tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_npm() -> CheckResult:
    """Check npm availability."""

    return check_tool(
        ToolDefinition(
            id="tool.npm",
            title="npm",
            executable="npm",
            install_hint="Install npm with Node.js or through your JavaScript runtime manager.",
            weight=1,
        )
    )
