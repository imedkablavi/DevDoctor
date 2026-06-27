"""Java runtime check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_java() -> CheckResult:
    """Check Java availability."""

    return check_tool(
        ToolDefinition(
            id="tool.java",
            title="Java",
            executable="java",
            version_args=("-version",),
            install_hint=(
                "Install an OpenJDK distribution such as Temurin, OpenJDK, or your distro package."
            ),
            weight=1,
        )
    )
