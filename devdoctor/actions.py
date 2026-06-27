"""Safe maintenance and fix action planning for the dashboard."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from devdoctor.models import CheckResult, CheckStatus
from devdoctor.package_managers import InstallPlan, install_plan_for_tool
from devdoctor.utils import format_bytes


@dataclass(frozen=True, slots=True)
class MaintenanceAction:
    """A user-confirmed maintenance or repair command."""

    id: str
    title: str
    description: str
    command: str
    estimated_freed: str
    requires_sudo: bool = False


def optimizer_actions() -> tuple[MaintenanceAction, ...]:
    """Return safe optimizer actions with best-effort space estimates."""

    home = Path.home()
    npm_cache = home / ".npm"
    pnpm_store = home / ".local/share/pnpm/store"
    pip_cache = home / ".cache/pip"
    flatpak_cache = home / ".var/app"
    temp_dir = Path("/tmp")

    return (
        MaintenanceAction(
            id="clean.package.cache",
            title="Clean package cache",
            description="Clean native package-manager caches where supported.",
            command=_first_available_command(
                (
                    ("dnf", "sudo dnf clean all"),
                    ("apt", "sudo apt clean"),
                    ("pacman", "sudo pacman -Sc"),
                ),
                fallback="No supported package cache command detected",
            ),
            estimated_freed="Unknown until package manager reports cache contents",
            requires_sudo=True,
        ),
        MaintenanceAction(
            id="clean.flatpak.cache",
            title="Clean Flatpak cache",
            description="Remove unused Flatpak runtimes and cached objects.",
            command="flatpak uninstall --unused",
            estimated_freed=_estimate_path(flatpak_cache),
        ),
        MaintenanceAction(
            id="clean.npm.cache",
            title="Clean npm cache",
            description="Verify and clean npm's local cache.",
            command="npm cache clean --force",
            estimated_freed=_estimate_path(npm_cache),
        ),
        MaintenanceAction(
            id="clean.pnpm.cache",
            title="Clean pnpm store",
            description="Prune unreferenced packages from the pnpm store.",
            command="pnpm store prune",
            estimated_freed=_estimate_path(pnpm_store),
        ),
        MaintenanceAction(
            id="clean.orphans",
            title="Remove orphan packages",
            description="Remove orphaned packages when the native package manager supports it.",
            command=_first_available_command(
                (
                    ("dnf", "sudo dnf autoremove"),
                    ("apt", "sudo apt autoremove"),
                    ("pacman", "sudo pacman -Rns $(pacman -Qtdq)"),
                ),
                fallback="No supported orphan-removal command detected",
            ),
            estimated_freed="Unknown until dependency resolver calculates removals",
            requires_sudo=True,
        ),
        MaintenanceAction(
            id="clean.docker.images",
            title="Remove unused Docker images",
            description="Prune dangling and unused Docker images.",
            command="docker image prune -a",
            estimated_freed="Docker calculates reclaimable space before confirmation",
        ),
        MaintenanceAction(
            id="clean.podman.images",
            title="Remove unused Podman images",
            description="Prune dangling and unused Podman images.",
            command="podman image prune -a",
            estimated_freed="Podman calculates reclaimable space before confirmation",
        ),
        MaintenanceAction(
            id="clean.tmp",
            title="Clean temporary files",
            description="Remove user-owned temporary files older than seven days.",
            command='find /tmp -user "$USER" -type f -mtime +7 -delete',
            estimated_freed=_estimate_path(temp_dir),
        ),
        MaintenanceAction(
            id="clean.journal",
            title="Clean journal logs",
            description="Vacuum systemd journal logs older than seven days.",
            command="sudo journalctl --vacuum-time=7d",
            estimated_freed="journalctl reports reclaimed space after vacuuming",
            requires_sudo=True,
        ),
        MaintenanceAction(
            id="clean.pip.cache",
            title="Clean pip cache",
            description="Purge pip's local download and wheel cache.",
            command="python -m pip cache purge",
            estimated_freed=_estimate_path(pip_cache),
        ),
    )


def auto_fix_plans(results: tuple[CheckResult, ...]) -> tuple[InstallPlan, ...]:
    """Return install plans for missing or failed tool checks."""

    plans: list[InstallPlan] = []
    seen: set[str] = set()
    for result in results:
        if result.status is CheckStatus.PASS or not result.id.startswith("tool."):
            continue
        if result.details.get("installed") is True:
            continue
        if result.id in seen:
            continue
        plan = install_plan_for_tool(result.id, result.title)
        if plan is not None:
            plans.append(plan)
            seen.add(result.id)
    return tuple(plans)


def _first_available_command(
    commands: tuple[tuple[str, str], ...],
    *,
    fallback: str,
) -> str:
    for executable, command in commands:
        if shutil.which(executable):
            return command
    return fallback


def _estimate_path(path: Path) -> str:
    max_files = 5_000
    try:
        if not path.exists():
            return "0 B"
        if path.is_file():
            return format_bytes(path.stat().st_size)
        total = 0
        scanned = 0
        for item in path.rglob("*"):
            if not item.is_file():
                continue
            total += item.stat().st_size
            scanned += 1
            if scanned >= max_files:
                return f"At least {format_bytes(total)}"
    except OSError:
        return "Unavailable"
    return format_bytes(total)
