from __future__ import annotations

from io import StringIO

from rich.console import Console
from typer.testing import CliRunner

from devdoctor import cli
from devdoctor.bootstrap import InstallPlan
from devdoctor.cli import app


def test_list_profiles_command() -> None:
    result = CliRunner().invoke(app, ["list", "profiles", "--no-color"])

    assert result.exit_code == 0
    assert "devops" in result.output
    assert "frontend" in result.output


def test_dry_run_never_falls_back_to_install_command(monkeypatch: object) -> None:
    executed: list[tuple[tuple[str, ...], ...]] = []

    def fake_execute(
        commands: tuple[tuple[str, ...], ...],
        *,
        yes: bool,
        console: Console,
    ) -> None:
        executed.append(commands)

    plan = InstallPlan(
        tool_id="example",
        tool_title="Example",
        manager="brew",
        command=("brew", "install", "example"),
        explanation="Install Example.",
        risk="low",
        dry_run_command=None,
    )
    monkeypatch.setattr(cli, "_execute_commands", fake_execute)

    cli._execute_plans(
        (plan,),
        dry_run=True,
        yes=False,
        console=Console(file=StringIO(), force_terminal=False),
    )

    assert executed == []


def test_dry_run_executes_only_dry_run_command(monkeypatch: object) -> None:
    executed: list[tuple[tuple[str, ...], ...]] = []
    confirmations: list[bool] = []

    def fake_execute(
        commands: tuple[tuple[str, ...], ...],
        *,
        yes: bool,
        console: Console,
    ) -> None:
        executed.append(commands)
        confirmations.append(yes)

    plan = InstallPlan(
        tool_id="git",
        tool_title="Git",
        manager="apt",
        command=("sudo", "apt", "install", "git"),
        explanation="Install Git.",
        risk="medium",
        dry_run_command=("apt", "install", "--dry-run", "git"),
    )
    monkeypatch.setattr(cli, "_execute_commands", fake_execute)

    cli._execute_plans(
        (plan,),
        dry_run=True,
        yes=False,
        console=Console(file=StringIO(), force_terminal=False),
    )

    assert executed == [(("apt", "install", "--dry-run", "git"),)]
    assert confirmations == [True]
