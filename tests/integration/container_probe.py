#!/usr/bin/env python3
"""Assertions executed inside Linux package-manager integration containers."""

from __future__ import annotations

import argparse

from devdoctor import bootstrap
from devdoctor.atomic_planning import apply_atomic_planning_patch
from devdoctor.fallback_planning import apply_fallback_planning_patch
from devdoctor.hardening import apply_runtime_hardening
from devdoctor.package_managers import (
    detect_package_managers,
    package_manager_conflicts,
)
from devdoctor.utils import read_os_release


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-manager", required=True)
    parser.add_argument("--expected-plan-manager")
    parser.add_argument("--forbid-plan-manager")
    parser.add_argument("--expected-conflict", action="append", default=[])
    args = parser.parse_args()

    apply_atomic_planning_patch()
    apply_fallback_planning_patch()
    apply_runtime_hardening()

    managers = detect_package_managers()
    installed = {manager.id for manager in managers if manager.installed}
    if args.expected_manager not in installed:
        raise AssertionError(
            f"expected manager {args.expected_manager!r}; detected {sorted(installed)!r}"
        )

    conflicts = {
        conflict.kind for conflict in package_manager_conflicts(managers, read_os_release())
    }
    missing_conflicts = set(args.expected_conflict) - conflicts
    if missing_conflicts:
        raise AssertionError(
            f"missing expected conflicts {sorted(missing_conflicts)!r}; got {sorted(conflicts)!r}"
        )

    if args.expected_plan_manager or args.forbid_plan_manager:
        system = bootstrap.detect_system_context(specs=bootstrap.get_bootstrap_tools())
        git_spec = next(spec for spec in bootstrap.get_bootstrap_tools() if spec.id == "git")
        plan = bootstrap.install_plan_for_spec(git_spec, system=system)
        if args.expected_plan_manager:
            if plan is None:
                raise AssertionError(
                    f"expected plan manager {args.expected_plan_manager!r}, got no plan"
                )
            if plan.manager != args.expected_plan_manager:
                raise AssertionError(
                    f"expected plan manager {args.expected_plan_manager!r}, got {plan.manager!r}"
                )
        if args.forbid_plan_manager and plan is not None and plan.manager == args.forbid_plan_manager:
            raise AssertionError(f"forbidden plan manager selected: {plan.manager!r}")

    print(
        "integration probe ok:",
        args.expected_manager,
        f"plan={args.expected_plan_manager or 'not-asserted'}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
