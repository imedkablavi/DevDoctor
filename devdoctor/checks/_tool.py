"""Reusable development tool detection helpers."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from devdoctor.models import CheckCategory, CheckResult, JsonValue
from devdoctor.utils import CommandResult, parse_version, run_command

CommandRunner = Callable[[Sequence[str], float], CommandResult]
WhichFunc = Callable[[str], str | None]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Metadata required to detect a command-line tool."""

    id: str
    title: str
    executable: str
    version_args: tuple[str, ...] = ("--version",)
    required: bool = False
    install_hint: str = ""
    weight: int = 1
    timeout: float = 5.0


def check_tool(
    definition: ToolDefinition,
    *,
    runner: CommandRunner = run_command,
    which_func: WhichFunc = shutil.which,
) -> CheckResult:
    """Detect a command-line tool, its path, and its version."""

    path = which_func(definition.executable)
    details: dict[str, JsonValue] = {
        "tool": definition.executable,
        "installed": bool(path),
        "path": path,
    }
    if not path:
        summary = f"{definition.title} is not installed."
        recommendation = (
            definition.install_hint or f"Install {definition.title} with your package manager."
        )
        if definition.required:
            return CheckResult.failure(
                id=definition.id,
                title=definition.title,
                category=CheckCategory.TOOL,
                summary=summary,
                details=details,
                recommendation=recommendation,
                weight=max(definition.weight, 3),
            )
        return CheckResult.warning(
            id=definition.id,
            title=definition.title,
            category=CheckCategory.TOOL,
            summary=summary,
            details=details,
            recommendation=recommendation,
            weight=definition.weight,
        )

    command = (path, *definition.version_args)
    version_result = runner(command, definition.timeout)
    version = parse_version(version_result.combined_output)
    details.update(
        {
            "version": version,
            "version_command": list(command),
            "version_returncode": version_result.returncode,
        }
    )
    if version_result.returncode == 124:
        return CheckResult.warning(
            id=definition.id,
            title=definition.title,
            category=CheckCategory.TOOL,
            summary=f"{definition.title} is installed, but version detection timed out.",
            details=details,
            recommendation=f"Run {' '.join(command)} manually to verify {definition.title}.",
            weight=1,
        )
    if version_result.returncode != 0 and not version:
        return CheckResult.warning(
            id=definition.id,
            title=definition.title,
            category=CheckCategory.TOOL,
            summary=f"{definition.title} is installed, but version detection failed.",
            details=details,
            recommendation=f"Check whether {definition.title} is configured correctly.",
            weight=1,
        )

    version_label = f" {version}" if version else ""
    return CheckResult.ok(
        id=definition.id,
        title=definition.title,
        category=CheckCategory.TOOL,
        summary=f"{definition.title}{version_label} is available.",
        details=details,
        weight=definition.weight,
    )
