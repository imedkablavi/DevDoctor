"""Conservative fallback package plans for managers not fully modeled in the legacy catalog."""

from __future__ import annotations

from collections.abc import Mapping

from devdoctor import bootstrap
from devdoctor.models import JsonValue
from devdoctor.package_managers import NIX_PACKAGES

_PATCHED = False


def _installed_manager_ids(system: Mapping[str, JsonValue]) -> set[str]:
    managers = system.get("package_managers", ())
    return {
        str(manager.get("id"))
        for manager in managers
        if isinstance(manager, dict) and manager.get("installed") is True
    }


def nix_plan_for_spec(
    spec: bootstrap.ToolSpec,
    *,
    system: Mapping[str, JsonValue],
) -> bootstrap.InstallPlan | None:
    """Return a user-profile Nix plan only for explicitly validated package mappings."""

    if "nix" not in _installed_manager_ids(system):
        return None
    package = NIX_PACKAGES.get(f"tool.{spec.id}")
    if package is None:
        return None
    command, dry_run, rollback = bootstrap._manager_commands("nix", package)
    if command is None:
        return None
    return bootstrap.InstallPlan(
        tool_id=spec.id,
        tool_title=spec.title,
        manager="nix",
        manager_reason=(
            "Nix is installed and DevDoctor has an explicit user-profile mapping for this tool."
        ),
        package_name=package,
        command=command,
        dry_run_command=dry_run,
        verify_command=bootstrap._verification_command(spec),
        rollback_command=rollback,
        explanation=f"Install {spec.title} in the current Nix profile using `{package}`.",
        risk=bootstrap._install_risk("nix"),
        requires_sudo=False,
        dependencies=tuple(dependency.tool_id for dependency in spec.tool_dependencies),
    )


def apply_fallback_planning_patch() -> None:
    """Add conservative Nix fallback after the normal/Atomic planner has declined a plan."""

    global _PATCHED
    if _PATCHED:
        return
    original = bootstrap.install_plan_for_spec

    def planner(
        spec: bootstrap.ToolSpec,
        *,
        system: Mapping[str, JsonValue],
    ) -> bootstrap.InstallPlan | None:
        plan = original(spec, system=system)
        if plan is not None:
            return plan
        return nix_plan_for_spec(spec, system=system)

    bootstrap.install_plan_for_spec = planner
    _PATCHED = True
