"""Atomic Fedora/Bazzite install planning for the main bootstrap catalog."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

from devdoctor import bootstrap
from devdoctor.models import JsonValue
from devdoctor.package_managers import ATOMIC_VARIANTS, NIX_PACKAGES
from devdoctor.utils import read_os_release

OriginalPlanner = Callable[..., bootstrap.InstallPlan | None]
_PATCHED = False
_NIX_CATALOG_KEYS = {
    "rustc": "tool.rust",
    "gh": "tool.github_cli",
}
_MANAGER_VERSION_BY_PATH: dict[str, str] = {}


def _installed_manager_ids(system: Mapping[str, JsonValue]) -> set[str]:
    managers = system.get("package_managers", ())
    return {
        str(manager.get("id"))
        for manager in managers
        if isinstance(manager, dict) and manager.get("installed") is True
    }


def _release_is_atomic(release: Mapping[str, str]) -> bool:
    distro_id = release.get("ID", "").lower()
    variant_id = release.get("VARIANT_ID", "").lower()
    image_id = release.get("IMAGE_ID", "").lower()
    return (
        distro_id == "bazzite"
        or variant_id in ATOMIC_VARIANTS
        or image_id in ATOMIC_VARIANTS
        or bool(release.get("OSTREE_VERSION"))
    )


def _system_is_atomic(system: Mapping[str, JsonValue]) -> bool:
    """Use the persisted host classification instead of re-probing managers per tool."""

    if "atomic_host" in system:
        return system.get("atomic_host") is True

    distro_id = str(system.get("distribution_id", "")).lower()
    if distro_id == "bazzite":
        return True

    installed = _installed_manager_ids(system)
    if "rpm-ostree" not in installed:
        return False

    distribution = str(system.get("distribution", "")).lower()
    if any(marker in distribution for marker in (*ATOMIC_VARIANTS, "atomic", "ostree")):
        return True

    return distro_id in {"ublue", "universal-blue"}


def _plan_for_manager(
    spec: bootstrap.ToolSpec,
    *,
    manager: str,
    package: str,
    reason: str,
) -> bootstrap.InstallPlan | None:
    command, dry_run, rollback = bootstrap._manager_commands(manager, package)
    if command is None:
        return None
    return bootstrap.InstallPlan(
        tool_id=spec.id,
        tool_title=spec.title,
        manager=manager,
        manager_reason=reason,
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


def _nix_package(spec: bootstrap.ToolSpec) -> str | None:
    key = _NIX_CATALOG_KEYS.get(spec.id, f"tool.{spec.id}")
    return spec.packages.get("nix") or NIX_PACKAGES.get(key)


def _mapped_user_space_package(spec: bootstrap.ToolSpec, manager: str) -> str | None:
    if manager == "nix":
        return _nix_package(spec)
    return spec.packages.get(manager)


def atomic_install_plan_for_spec(
    spec: bootstrap.ToolSpec,
    *,
    system: Mapping[str, JsonValue],
    original: OriginalPlanner,
) -> bootstrap.InstallPlan | None:
    """Build a user-space-first Atomic plan, layering only as a final fallback."""

    if not _system_is_atomic(system):
        return original(spec, system=system)

    installed = _installed_manager_ids(system)

    for manager in ("brew", "flatpak", "nix", "cargo", "npm", "pnpm", "pipx", "pip"):
        if manager not in installed:
            continue
        package = _mapped_user_space_package(spec, manager)
        if package is None:
            continue
        plan = _plan_for_manager(
            spec,
            manager=manager,
            package=package,
            reason=(
                "Atomic/image-based host: prefer a mapped user-space or package-scoped manager "
                "before layering the base image."
            ),
        )
        if plan is not None:
            return plan

    if "rpm-ostree" in installed:
        package = spec.packages.get("rpm-ostree") or spec.packages.get("dnf")
        if package:
            plan = _plan_for_manager(
                spec,
                manager="rpm-ostree",
                package=package,
                reason=(
                    "Atomic/image-based host: no mapped user-space option is available, so use "
                    "rpm-ostree layering for the Fedora package mapping; DNF host mutation is "
                    "intentionally suppressed."
                ),
            )
            if plan is not None:
                return plan

    return None


def apply_atomic_planning_patch() -> None:
    """Patch planning/context once so every CLI path shares one Atomic classification."""

    global _PATCHED
    if _PATCHED:
        return

    original_planner = bootstrap.install_plan_for_spec
    original_context = bootstrap.detect_system_context
    original_tool_version = bootstrap._tool_version

    def detect_system_context(
        *,
        specs: object = None,
    ) -> Mapping[str, JsonValue]:
        context = dict(original_context(specs=specs))
        context["atomic_host"] = _release_is_atomic(read_os_release())

        _MANAGER_VERSION_BY_PATH.clear()
        managers = context.get("package_managers", ())
        if isinstance(managers, list):
            for manager in managers:
                if not isinstance(manager, Mapping):
                    continue
                path = manager.get("path")
                version = manager.get("version")
                if isinstance(path, str) and isinstance(version, str) and version:
                    _MANAGER_VERSION_BY_PATH[path] = version
        return context

    def tool_version(path: str | None, version_args: Sequence[str]) -> str | None:
        if path is not None:
            cached = _MANAGER_VERSION_BY_PATH.get(path)
            if cached is not None:
                return cached
        return original_tool_version(path, version_args)

    def planner(
        spec: bootstrap.ToolSpec,
        *,
        system: Mapping[str, JsonValue],
    ) -> bootstrap.InstallPlan | None:
        return atomic_install_plan_for_spec(spec, system=system, original=original_planner)

    bootstrap.detect_system_context = detect_system_context
    bootstrap._tool_version = tool_version
    bootstrap.install_plan_for_spec = planner
    _PATCHED = True
