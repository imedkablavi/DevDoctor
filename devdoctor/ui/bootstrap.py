"""Rich output for bootstrap inventory commands."""

from __future__ import annotations

from collections.abc import Iterable

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devdoctor import __version__
from devdoctor.bootstrap import (
    BootstrapCategory,
    BootstrapInventory,
    BootstrapProfile,
    InstallPlan,
    ToolDetection,
)


def bootstrap_group(
    inventory: BootstrapInventory,
    *,
    show_missing_only: bool = False,
) -> Group:
    """Render a full bootstrap inventory."""

    renderables: list[object] = [
        bootstrap_header(inventory),
        system_context_panel(inventory),
    ]

    for category, detections in inventory.categories().items():
        visible = tuple(
            detection
            for detection in detections
            if not show_missing_only or not detection.installed
        )
        if visible:
            renderables.append(category_table(category, visible))

    plans = tuple(
        detection.install_plan
        for detection in inventory.missing
        if detection.install_plan is not None
    )
    if plans:
        renderables.append(install_plans_table(plans))

    broken = inventory.broken
    if broken:
        renderables.append(repair_suggestions_table(broken))

    return Group(*renderables)


def bootstrap_header(inventory: BootstrapInventory) -> Panel:
    """Render the command header and inventory counts."""

    summary = inventory.to_dict()["summary"]
    grid = Table.grid(expand=True)
    grid.add_column(ratio=2)
    grid.add_column(justify="right", no_wrap=True)

    title = Text()
    title.append("Dev", style="brand")
    title.append("Doctor", style="bold white")
    title.append(f"  v{__version__}", style="muted")
    title.append("\nLinux developer workstation bootstrap", style="tagline")

    counts = Text()
    counts.append(f"{summary['installed']} installed", style="success")
    counts.append("  ")
    counts.append(f"{summary['missing']} missing", style="error")
    counts.append("  ")
    counts.append(f"{summary['broken']} broken", style="warning")

    grid.add_row(title, counts)
    return Panel(grid, border_style="bright_cyan", box=box.SIMPLE, padding=(1, 2))


def system_context_panel(inventory: BootstrapInventory) -> Panel:
    """Render detected host context."""

    system = inventory.system
    managers = [
        str(manager.get("id"))
        for manager in system.get("package_managers", ())
        if isinstance(manager, dict) and manager.get("installed") is True
    ]

    table = Table.grid(expand=True, padding=(0, 1))
    table.add_column(style="muted", no_wrap=True)
    table.add_column(ratio=1)
    table.add_column(style="muted", no_wrap=True)
    table.add_column(ratio=1)
    table.add_row(
        "OS", str(system.get("distribution", "unknown")), "Arch", str(system.get("architecture"))
    )
    table.add_row(
        "Shell",
        str(system.get("shell", "unknown")),
        "Desktop",
        str(system.get("desktop_environment")),
    )
    table.add_row(
        "Session",
        str(system.get("session_type", "unknown")),
        "Terminal",
        str(system.get("terminal")),
    )
    table.add_row(
        "Virtualization",
        str(system.get("virtualization")),
        "Container",
        str(system.get("is_container")),
    )
    table.add_row("WSL", str(system.get("is_wsl")), "Sudo", str(system.get("can_sudo")))
    table.add_row(
        "Managers",
        ", ".join(managers) or "none detected",
        "PATH issues",
        str(system.get("path_issue_count", 0)),
    )
    return Panel(table, title="Host", border_style="bright_black", box=box.SIMPLE)


def category_table(
    category: BootstrapCategory,
    detections: Iterable[ToolDetection],
) -> Table:
    """Render tools in one bootstrap category."""

    table = Table(
        title=category.value,
        box=box.SIMPLE,
        border_style="bright_black",
        header_style="bold white",
        expand=True,
        show_lines=False,
    )
    table.add_column("", width=2, no_wrap=True)
    table.add_column("Tool", min_width=14, ratio=2)
    table.add_column("Version", no_wrap=True, ratio=1)
    table.add_column("Path", ratio=3, overflow="fold")
    table.add_column("Install", ratio=3, overflow="fold")

    for detection in detections:
        table.add_row(
            _status_icon(detection),
            detection.spec.title,
            detection.version or "",
            detection.executable_path or "",
            _plan_text(detection),
        )
    return table


def install_plans_table(plans: Iterable[InstallPlan]) -> Table:
    """Render missing-tool install plans."""

    table = Table(
        title="Install plans",
        box=box.SIMPLE,
        border_style="bright_black",
        header_style="bold white",
        expand=True,
    )
    table.add_column("Tool", min_width=14)
    table.add_column("Manager", no_wrap=True)
    table.add_column("Risk", ratio=1)
    table.add_column("Command", ratio=3, overflow="fold")
    table.add_column("Dry run", ratio=3, overflow="fold")

    for plan in plans:
        table.add_row(
            plan.tool_title,
            plan.manager,
            plan.risk.split(" - ", 1)[0],
            " ".join(plan.command),
            " ".join(plan.dry_run_command) if plan.dry_run_command else "",
        )
    return table


def repair_suggestions_table(detections: Iterable[ToolDetection]) -> Table:
    """Render real repair suggestions for detected local problems."""

    table = Table(
        title="Repair suggestions",
        box=box.SIMPLE,
        border_style="yellow",
        header_style="bold white",
        expand=True,
    )
    table.add_column("Tool", min_width=14)
    table.add_column("Problem", ratio=2)
    table.add_column("Suggested action", ratio=3, overflow="fold")

    for detection in detections:
        for problem, action in _repair_actions(detection):
            table.add_row(detection.spec.title, problem, action)
    return table


def profiles_table(profiles: Iterable[BootstrapProfile]) -> Table:
    """Render available bootstrap profiles."""

    table = Table(
        title="Profiles",
        box=box.SIMPLE,
        border_style="bright_black",
        header_style="bold white",
        expand=True,
    )
    table.add_column("Profile", no_wrap=True)
    table.add_column("Description", ratio=2)
    table.add_column("Tools", ratio=3, overflow="fold")
    for profile in profiles:
        table.add_row(profile.id, profile.description, ", ".join(profile.tool_ids))
    return table


def compact_inventory_status(inventory: BootstrapInventory) -> str:
    """Return a compact one-line inventory summary for scripts."""

    summary = inventory.to_dict()["summary"]
    return (
        f"installed={summary['installed']} missing={summary['missing']} "
        f"broken={summary['broken']} total={summary['total']}"
    )


def compact_plan_status(plans: Iterable[InstallPlan]) -> str:
    """Return install commands as compact script-friendly lines."""

    return "\n".join(f"{plan.tool_id}: {plan.command_text}" for plan in plans)


def _status_icon(detection: ToolDetection) -> Text:
    if detection.broken_installation:
        return Text("!", style="warning")
    if detection.installed:
        return Text("✓", style="success")
    return Text("✗", style="error")


def _plan_text(detection: ToolDetection) -> str:
    if detection.installed:
        return ""
    if detection.install_plan is None:
        return "No supported local manager detected"
    return detection.install_plan.command_text


def _repair_actions(detection: ToolDetection) -> tuple[tuple[str, str], ...]:
    actions: list[tuple[str, str]] = []
    for issue in detection.permission_issues:
        if detection.executable_path:
            actions.append((issue, f"Review ownership and mode: ls -l {detection.executable_path}"))
    for issue in detection.path_issues:
        if detection.executable_path:
            actions.append(
                (issue, f"Remove or relink stale executable: {detection.executable_path}")
            )
    for dependency in detection.missing_dependencies:
        actions.append(
            (
                f"Missing dependency: {dependency}",
                f"Install dependency before using {detection.spec.title}.",
            )
        )
    if not actions and detection.broken_installation:
        actions.append(
            ("Broken installation", "Reinstall the tool with the package manager that owns it.")
        )
    return tuple(actions)
