"""Atomic Fedora/Bazzite install planning for the main bootstrap catalog."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from devdoctor import bootstrap
from devdoctor.models import JsonValue
from devdoctor.package_managers import detect_package_managers, is_atomic_host
from devdoctor.utils import read_os_release

OriginalPlanner = Callable[..., bootstrap.InstallPlan | None]
_PATCHED = False


def _installed_manager_ids(system: Mapping[str, JsonValue]) -> set[str]:
    managers = system.get("package_managers", ())
    return {
        str(manager.get("id"))
        for manager in managers
        if isinstance(manager, dict) and manager.get("installed") is True
    }


def _system_is_atomic(system: Mapping[str, JsonValue]) -> bool:
    distro_id = str(system.get("distribution_id", "")).lower()
    if distro_id == "bazzite":
        return True
    return is_atomic_host(read_os_release(), detect_package_managers())


def atomic_install_plan_for_spec(
    spec: bootstrap.ToolSpec,
    *,
    system: Mapping[str, JsonValue],
    original: OriginalPlanner,
) -> bootstrap.InstallPlan | None:
    """Build a user-space-first Atomic plan, reusing Fedora package names for layering."""

    if not _system_is_atomic(system):
        return original(spec, system=system)

    installed = _installed_manager_ids(system)

    if "brew" in installed and "brew" in spec.packages:
        package = spec.packages["brew"]
        command, dry_run, rollback = bootstrap._manager_commands("brew", package)
        if command is not None:
            return bootstrap.InstallPlan(
                tool_id=spec.id,
                tool_title=spec.title,
                manager="brew",
                manager_reason=(
                    "Atomic/image-based host: prefer a user-space Homebrew install before "
                    "layering the base image."
                ),
                package_name=package,
                command=command,
                dry_run_command=dry_run,
                verify_command=bootstrap._verification_command(spec),
                rollback_command=rollback,
                explanation=(
                    f"Install {spec.title} in user space with Homebrew package `{package}`."
                ),
                risk=bootstrap._install_risk("brew"),
                requires_sudo=bootstrap._requires_sudo(command),
                dependencies=tuple(dependency.tool_id for dependency in spec.tool_dependencies),
            )

    if "rpm-ostree" in installed:
        package = spec.packages.get("rpm-ostree") or spec.packages.get("dnf")
        if package:
            command, dry_run, rollback = bootstrap._manager_commands("rpm-ostree", package)
            if command is not None:
                return bootstrap.InstallPlan(
                    tool_id=spec.id,
                    tool_title=spec.title,
                    manager="rpm-ostree",
                    manager_reason=(
                        "Atomic/image-based host: use rpm-ostree layering for the Fedora package "
                        "mapping; DNF host mutation is intentionally suppressed."
                    ),
                    package_name=package,
                    command=command,
                    dry_run_command=dry_run,
                    verify_command=bootstrap._verification_command(spec),
                    rollback_command=rollback,
                    explanation=(
                        f"Layer Fedora package `{package}` for {spec.title} with rpm-ostree. "
                        "A reboot may be required."
                    ),
                    risk=bootstrap._install_risk("rpm-ostree"),
                    requires_sudo=bootstrap._requires_sudo(command),
                    dependencies=tuple(dependency.tool_id for dependency in spec.tool_dependencies),
                )

    # Desktop/user-space mappings can remain useful, but never fall through to DNF.
    for manager in ("flatpak", "nix", "cargo", "npm", "pnpm", "pipx", "pip"):
        if manager not in installed or manager not in spec.packages:
            continue
        package = spec.packages[manager]
        command, dry_run, rollback = bootstrap._manager_commands(manager, package)
        if command is None:
            continue
        return bootstrap.InstallPlan(
            tool_id=spec.id,
            tool_title=spec.title,
            manager=manager,
            manager_reason="Atomic/image-based host: selected a mapped non-DNF package manager.",
            package_name=package,
            command=command,
            dry_run_command=dry_run,
            verify_command=bootstrap._verification_command(spec),
            rollback_command=rollback,
            explanation=f"Install {spec.title} using {manager} package `{package}`.",
            risk=bootstrap._install_risk(manager),
            requires_sudo=bootstrap._requires_sudo(command),
            dependencies=tuple(dependency.tool_id for dependency in spec.tool_dependencies),
        )
    return None


def apply_atomic_planning_patch() -> None:
    """Patch the bootstrap planner once so every CLI path receives Atomic-safe plans."""

    global _PATCHED
    if _PATCHED:
        return
    original = bootstrap.install_plan_for_spec

    def planner(
        spec: bootstrap.ToolSpec,
        *,
        system: Mapping[str, JsonValue],
    ) -> bootstrap.InstallPlan | None:
        return atomic_install_plan_for_spec(spec, system=system, original=original)

    bootstrap.install_plan_for_spec = planner
    _PATCHED = True
