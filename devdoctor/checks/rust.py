"""Rust compiler check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckResult


def check_rust() -> CheckResult:
    """Check rustc availability."""

    return check_tool(
        ToolDefinition(
            id="tool.rust",
            title="Rust",
            executable="rustc",
            install_hint="Install Rust with rustup from https://rustup.rs.",
            weight=1,
        )
    )
