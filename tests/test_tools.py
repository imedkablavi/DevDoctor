from __future__ import annotations

from collections.abc import Sequence

from devdoctor.checks._tool import ToolDefinition, check_tool
from devdoctor.models import CheckStatus
from devdoctor.utils import CommandResult


def test_check_tool_reports_missing_required_tool_as_failure() -> None:
    result = check_tool(
        ToolDefinition(
            id="tool.git",
            title="Git",
            executable="git",
            required=True,
            install_hint="Install Git.",
            weight=4,
        ),
        which_func=lambda _name: None,
    )

    assert result.status is CheckStatus.FAIL
    assert result.details["installed"] is False
    assert result.recommendation == "Install Git."


def test_check_tool_detects_installed_version_and_path() -> None:
    def runner(command: Sequence[str], timeout: float) -> CommandResult:
        return CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="example version 1.2.3\n",
            stderr="",
            duration_seconds=0.01,
        )

    result = check_tool(
        ToolDefinition(
            id="tool.example",
            title="Example",
            executable="example",
        ),
        runner=runner,
        which_func=lambda _name: "/usr/bin/example",
    )

    assert result.status is CheckStatus.PASS
    assert result.details["path"] == "/usr/bin/example"
    assert result.details["version"] == "1.2.3"


def test_check_tool_warns_when_version_command_times_out() -> None:
    def runner(command: Sequence[str], timeout: float) -> CommandResult:
        return CommandResult(
            command=tuple(command),
            returncode=124,
            stdout="",
            stderr="timed out",
            duration_seconds=timeout,
        )

    result = check_tool(
        ToolDefinition(
            id="tool.example",
            title="Example",
            executable="example",
        ),
        runner=runner,
        which_func=lambda _name: "/usr/bin/example",
    )

    assert result.status is CheckStatus.WARNING
    assert "timed out" in result.summary
