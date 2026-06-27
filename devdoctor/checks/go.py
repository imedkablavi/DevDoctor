"""Go toolchain check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_go() -> CheckResult:
    """Check Go availability."""

    return check_tool(
        ToolDefinition(
            id="tool.go",
            title="Go",
            executable="go",
            version_args=("version",),
            install_hint=(
                "Install Go through your distribution, asdf, mise, or the official tarball."
            ),
            weight=1,
        )
    )
