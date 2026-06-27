"""Node.js tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_node() -> CheckResult:
    """Check Node.js availability."""

    return check_tool(
        ToolDefinition(
            id="tool.node",
            title="Node.js",
            executable="node",
            version_args=("--version",),
            install_hint="Install Node.js through your distro, nvm, fnm, Volta, or asdf.",
            weight=1,
        )
    )
