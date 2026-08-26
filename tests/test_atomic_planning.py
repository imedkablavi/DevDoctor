from __future__ import annotations

from devdoctor import atomic_planning, bootstrap


def _git_spec() -> bootstrap.ToolSpec:
    return next(spec for spec in bootstrap.get_bootstrap_tools() if spec.id == "git")


def _system(*manager_ids: str, distribution_id: str = "bazzite") -> dict[str, object]:
    return {
        "distribution": "Bazzite" if distribution_id == "bazzite" else "Fedora Linux 42",
        "distribution_id": distribution_id,
        "package_managers": [{"id": manager_id, "installed": True} for manager_id in manager_ids],
    }


def test_release_classification_requires_real_atomic_release_evidence() -> None:
    assert atomic_planning._release_is_atomic({"ID": "bazzite"}) is True
    assert (
        atomic_planning._release_is_atomic(
            {"ID": "fedora", "VARIANT_ID": "silverblue", "OSTREE_VERSION": "42.20260827"}
        )
        is True
    )
    assert atomic_planning._release_is_atomic({"ID": "fedora"}) is False


def test_persisted_atomic_host_flag_overrides_rpm_ostree_presence() -> None:
    mutable_fedora = {
        "atomic_host": False,
        "distribution": "Fedora Linux 42",
        "distribution_id": "fedora",
        "package_managers": [{"id": "rpm-ostree", "installed": True}],
    }
    atomic_fedora = {**mutable_fedora, "atomic_host": True}

    assert atomic_planning._system_is_atomic(mutable_fedora) is False
    assert atomic_planning._system_is_atomic(atomic_fedora) is True


def test_atomic_detection_uses_collected_system_context() -> None:
    assert atomic_planning._system_is_atomic(_system("rpm-ostree", "dnf")) is True
    assert (
        atomic_planning._system_is_atomic(
            {
                "distribution": "Fedora Linux 42 (Silverblue)",
                "distribution_id": "fedora",
                "package_managers": [{"id": "rpm-ostree", "installed": True}],
            }
        )
        is True
    )
    assert atomic_planning._system_is_atomic(_system("dnf", distribution_id="fedora")) is False


def test_atomic_main_planner_reuses_fedora_mapping_for_rpm_ostree() -> None:
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


def test_atomic_main_planner_prefers_homebrew_when_mapped() -> None:
    plan = atomic_planning.atomic_install_plan_for_spec(
        _git_spec(),
        system=_system("brew", "rpm-ostree", "dnf"),
        original=lambda spec, system: None,
    )

    assert plan is not None
    assert plan.manager == "brew"
    assert plan.command == ("brew", "install", "git")


def test_atomic_main_planner_prefers_mapped_user_space_manager_before_layering() -> None:
    spec = bootstrap.ToolSpec(
        id="example-node-tool",
        title="Example Node Tool",
        category=bootstrap.BootstrapCategory.DEVOPS,
        executable="example-node-tool",
        packages={"dnf": "example-node-tool", "npm": "example-node-tool"},
    )

    plan = atomic_planning.atomic_install_plan_for_spec(
        spec,
        system=_system("npm", "rpm-ostree", "dnf"),
        original=lambda spec, system: None,
    )

    assert plan is not None
    assert plan.manager == "npm"
    assert plan.command == ("npm", "install", "-g", "example-node-tool")


def test_atomic_main_planner_prefers_explicit_nix_mapping_before_layering() -> None:
    plan = atomic_planning.atomic_install_plan_for_spec(
        _git_spec(),
        system=_system("nix", "rpm-ostree", "dnf"),
        original=lambda spec, system: None,
    )

    assert plan is not None
    assert plan.manager == "nix"
    assert plan.command == ("nix", "profile", "install", "nixpkgs#git")


def test_atomic_main_planner_never_falls_back_to_original_dnf() -> None:
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
