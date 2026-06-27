"""Podman tool check."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import run_command


def check_podman() -> CheckResult:
    """Check Podman CLI availability and basic runtime access."""

    base = check_tool(
        ToolDefinition(
            id="tool.podman",
            title="Podman",
            executable="podman",
            install_hint=(
                "Install Podman if you use daemonless containers or Fedora-family workflows."
            ),
            weight=1,
        )
    )
    if not base.passed:
        return base

    path = str(base.details.get("path") or "podman")
    info = run_command((path, "info", "--format", "json"), timeout=5)
    details = dict(base.details)
    details["runtime_accessible"] = info.returncode == 0
    if info.returncode != 0:
        details["runtime_error"] = info.combined_output[-400:]
        return CheckResult.warning(
            id=base.id,
            title=base.title,
            category=CheckCategory.TOOL,
            summary="Podman CLI is installed, but runtime information is unavailable.",
            details=details,
            recommendation=(
                "Run `podman info` manually and verify your Podman storage configuration."
            ),
            weight=1,
        )
    return CheckResult.ok(
        id=base.id,
        title=base.title,
        category=CheckCategory.TOOL,
        summary=base.summary,
        details=details,
        weight=base.weight,
    )
