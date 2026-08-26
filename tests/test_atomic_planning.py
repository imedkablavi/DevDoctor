from __future__ import annotations

from devdoctor import atomic_planning, bootstrap


def _git_spec() -> bootstrap.ToolSpec:
    return next(spec for spec in bootstrap.get_bootstrap_tools() if spec.id == "git")


def _system(*manager_ids: str) -> dict[str, object]:
    return {
        "distribution_id": "bazzite",
        "package_managers": [{"id": manager_id, "installed": True} for manager_id in manager_ids],
    }


def test_atomic_main_planner_reuses_fedora_mapping_for_rpm_ostree(monkeypatch: object) -> None:
    monkeypatch.setattr(atomic_planning, "_system_is_atomic", lambda system: True)

    plan = atomic_planning.atomic_install_plan_for_spec(
        _git_spec(),
        system=_system("dnf", "rpm-ostree", "flatpak"),
        original=lambda spec, system: None,
    )

    assert plan is not None
    assert plan.manager == "rpm-ostree"
    assert plan.command == ("rpm-ostree", "install", "git")
    assert plan.dry_run_command is None
    assert plan.rollback_command == ("rpm-ostree", "uninstall", "git")
    assert "dnf" not in plan.command


def test_atomic_main_planner_prefers_homebrew_when_mapped(monkeypatch: object) -> None:
    monkeypatch.setattr(atomic_planning, "_system_is_atomic", lambda system: True)

    plan = atomic_planning.atomic_install_plan_for_spec(
        _git_spec(),
        system=_system("brew", "rpm-ostree", "dnf"),
        original=lambda spec, system: None,
    )

    assert plan is not None
    assert plan.manager == "brew"
    assert plan.command == ("brew", "install", "git")


def test_atomic_main_planner_never_falls_back_to_original_dnf(monkeypatch: object) -> None:
    monkeypatch.setattr(atomic_planning, "_system_is_atomic", lambda system: True)
    called = False

    def original(spec: object, *, system: object) -> bootstrap.InstallPlan | None:
        nonlocal called
        called = True
        raise AssertionError("original mutable-host planner must not run on Atomic")

    plan = atomic_planning.atomic_install_plan_for_spec(
        _git_spec(),
        system=_system("dnf"),
        original=original,
    )

    assert plan is None
    assert called is False
