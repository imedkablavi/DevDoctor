"""Cargo tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_cargo() -> CheckResult:
    """Check Cargo availability."""

    return check_tool(
        ToolDefinition(
            id="tool.cargo",
            title="Cargo",
            executable="cargo",
            install_hint="Install Cargo with rustup or your distribution's Rust package set.",
            weight=1,
        )
    )
