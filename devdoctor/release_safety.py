"""Release-safety overrides for commands that mutate an installed workstation.

This module is intentionally small and conservative. It protects the public
entry point while the older command implementations are refactored into the
central planner/executor architecture.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from typing import Annotated, Any

import typer

from devdoctor import bootstrap, cli
from devdoctor.bootstrap import InstallPlan, ToolDetection
from devdoctor.models import JsonValue
from devdoctor.utils import run_command

_RELEASE_DISTRIBUTION = "devdoctor-cli"


def self_update_command() -> tuple[str, ...]:
    """Return the command that upgrades the distribution backing DevDoctor."""

    return (sys.executable, "-m", "pip", "install", "--upgrade", _RELEASE_DISTRIBUTION)


def _is_atomic_system(system: Mapping[str, JsonValue]) -> bool:
    distro_id = str(system.get("distribution_id", "")).lower()
    if distro_id == "bazzite":
        return True
    managers = {
        str(item.get("id"))
        for item in system.get("package_managers", ())
        if isinstance(item, Mapping) and item.get("installed") is True
    }
    return "rpm-ostree" in managers and distro_id in {"fedora", "ublue", "universal-blue"}


def _owner_package(detection: ToolDetection) -> tuple[str | None, str | None]:
    """Resolve a canonical owning package for the selected executable."""

    path = detection.executable_path
    if not path:
        return None, None

    manager = detection.package_manager
    if manager == "dpkg":
        result = run_command(("dpkg-query", "-S", path), timeout=4)
        if result.returncode == 0 and result.combined_output:
            package = result.combined_output.splitlines()[0].split(":", 1)[0].strip()
            return "apt", package or None
        return None, None

    if manager == "rpm":
        result = run_command(("rpm", "-qf", "--qf", "%{NAME}", path), timeout=4)
        if result.returncode == 0 and result.combined_output:
            return "rpm", result.combined_output.strip().splitlines()[0]
        return None, None

    if manager == "pacman":
        result = run_command(("pacman", "-Qo", path), timeout=4)
        if result.returncode == 0 and result.combined_output:
            match = re.search(r" is owned by ([^\s]+) ", result.combined_output)
            if match:
                return "pacman", match.group(1)
        return None, None

    if detection.installation_method == "homebrew path":
        return "brew", detection.spec.packages.get("brew")

    return None, None


def uninstall_plan_for_detection(
    detection: ToolDetection,
    *,
    system: Mapping[str, JsonValue],
) -> InstallPlan | None:
    """Build an uninstall plan only when ownership is sufficiently proven.

    DevDoctor deliberately refuses to infer removal from the preferred install
    manager. Removing a package is allowed only when the selected executable's
    detected owner agrees with the catalog mapping. Atomic RPM ownership is not
    enough evidence that a package is layered, so it fails closed.
    """

    if not detection.installed:
        return None

    manager, owned_package = _owner_package(detection)
    if manager is None or owned_package is None:
        return None

    if manager == "rpm":
        if _is_atomic_system(system):
            return None
        manager = "dnf"

    expected_package = detection.spec.packages.get(manager)
    if expected_package is None or expected_package != owned_package:
        return None

    _, _, rollback = bootstrap._manager_commands(manager, owned_package)
    if rollback is None:
        return None

    return InstallPlan(
        tool_id=detection.spec.id,
        tool_title=detection.spec.title,
        manager=manager,
        manager_reason="Detected executable ownership matches the catalog package mapping.",
        package_name=owned_package,
        command=rollback,
        explanation=f"Remove {detection.spec.title} using its detected owner: {manager}.",
        risk=bootstrap._install_risk(manager),
        requires_sudo=bootstrap._requires_sudo(rollback),
        verify_command=(),
    )


def safe_self_update(
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Run the self-update command after confirmation."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Do not ask for confirmation."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable terminal colors."),
    ] = False,
) -> None:
    """Preview or upgrade the published ``devdoctor-cli`` distribution."""

    console = cli.create_console(no_color=no_color)
    command = self_update_command()
    console.print(" ".join(command))
    if apply:
        cli._execute_commands((command,), yes=yes, console=console, operation="self-update")
    else:
        console.print("[muted]No changes made. Use --apply to execute the self-update.[/muted]")


def safe_uninstall(
    tools: Annotated[
        list[str],
        typer.Argument(help="Tool IDs to remove only when installed ownership can be proven."),
    ],
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Execute verified uninstall commands after confirmation."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Do not ask for per-command confirmation."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable terminal colors."),
    ] = False,
) -> None:
    """Preview or execute ownership-verified uninstall commands."""

    console = cli.create_console(no_color=no_color)
    specs = cli._resolve_tool_specs(tuple(tools))
    inventory = bootstrap.bootstrap_inventory(include_ids=tuple(spec.id for spec in specs))
    by_id = {detection.spec.id: detection for detection in inventory.detections}

    plans: list[InstallPlan] = []
    refused: list[str] = []
    for spec in specs:
        detection = by_id.get(spec.id)
        if detection is None or not detection.installed:
            refused.append(f"{spec.id}: tool is not installed")
            continue
        plan = uninstall_plan_for_detection(detection, system=inventory.system)
        if plan is None:
            refused.append(
                f"{spec.id}: ownership is ambiguous or removal is unsafe on this host"
            )
            continue
        plans.append(plan)

    if refused:
        for message in refused:
            console.print(f"[warning]{message}[/warning]")

    if not plans:
        console.print("[error]No ownership-verified uninstall commands are available.[/error]")
        raise typer.Exit(code=1)

    console.print(cli.compact_plan_status(plans))
    if apply:
        cli._execute_plans(
            tuple(plans),
            dry_run=False,
            yes=yes,
            console=console,
            operation="uninstall",
        )
    else:
        console.print("[muted]No changes made. Use --apply to execute uninstall commands.[/muted]")


def _command_name(command: Any) -> str:
    explicit = getattr(command, "name", None)
    if explicit:
        return str(explicit)
    callback = getattr(command, "callback", None)
    name = getattr(callback, "__name__", "")
    return name.replace("_", "-")


def apply_release_safety(app: typer.Typer) -> None:
    """Replace legacy mutating callbacks before Typer builds the public CLI."""

    replacements = {
        "self-update": safe_self_update,
        "uninstall": safe_uninstall,
    }
    for command in app.registered_commands:
        replacement = replacements.get(_command_name(command))
        if replacement is not None:
            command.callback = replacement
