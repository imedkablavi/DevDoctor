"""Git tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_git() -> CheckResult:
    """Check Git availability."""

    return check_tool(
        ToolDefinition(
            id="tool.git",
            title="Git",
            executable="git",
            required=True,
            install_hint="Install Git with your distribution package manager.",
            weight=4,
        )
    )
