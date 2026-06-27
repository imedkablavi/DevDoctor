"""Docker tool and daemon checks."""

from __future__ import annotations

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import run_command


def check_docker() -> CheckResult:
    """Check Docker CLI availability and daemon access."""

    base = check_tool(
        ToolDefinition(
            id="tool.docker",
            title="Docker",
            executable="docker",
            install_hint=(
                "Install Docker Engine or Docker Desktop, or use Podman if your "
                "workflow prefers it."
            ),
            weight=1,
        )
    )
    if not base.passed:
        return base

    path = str(base.details.get("path") or "docker")
    info = run_command((path, "info", "--format", "{{json .ServerVersion}}"), timeout=4)
    details = dict(base.details)
    details["daemon_accessible"] = info.returncode == 0
    if info.returncode != 0:
        details["daemon_error"] = info.combined_output[-400:]
        return CheckResult.warning(
            id=base.id,
            title=base.title,
            category=CheckCategory.TOOL,
            summary="Docker CLI is installed, but the daemon is not reachable.",
            details=details,
            recommendation=(
                "Start the Docker service or verify your user has permission "
                "to access the Docker socket."
            ),
            weight=2,
        )
    return CheckResult.ok(
        id=base.id,
        title=base.title,
        category=CheckCategory.TOOL,
        summary=base.summary,
        details=details,
        weight=base.weight,
    )
