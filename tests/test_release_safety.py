from __future__ import annotations

import typer

from devdoctor import release_safety
from devdoctor.bootstrap import BootstrapCategory, HealthState, ToolDetection, ToolSpec
from devdoctor.utils import CommandResult


def _detection(
    *,
    package_manager: str | None,
    packages: dict[str, str],
    installation_method: str | None = None,
) -> ToolDetection:
    spec = ToolSpec(
        id="git",
        title="Git",
        category=BootstrapCategory.GIT_UTILITIES,
        executable="git",
        packages=packages,
    )
    return ToolDetection(
        spec=spec,
        installed=True,
        executable_path="/usr/bin/git",
        version="2.45.0",
        package_manager=package_manager,
        package_name=None,
        config_locations=(),
        alternate_paths=(),
        installation_method=installation_method,
        health=HealthState.READY,
        broken_installation=False,
        permission_issues=(),
        path_issues=(),
        missing_dependencies=(),
        dependency_status=(),
        repair_recommendations=(),
        install_plan=None,
    )


def _result(command: tuple[str, ...], output: str) -> CommandResult:
    return CommandResult(
        command=command,
        returncode=0,
        stdout=output,
        stderr="",
        duration_seconds=0.01,
    )


def test_self_update_uses_published_distribution_name() -> None:
    command = release_safety.self_update_command()

    assert command[-1] == "devdoctor-workstation"
    assert command[-1] != "devdoctor-cli"
    assert command[-1] != "devdoctor"


def test_uninstall_uses_detected_dpkg_owner(monkeypatch: object) -> None:
    detection = _detection(package_manager="dpkg", packages={"apt": "git"})

    monkeypatch.setattr(
        release_safety,
        "run_command",
        lambda command, timeout=4: _result(tuple(command), "git: /usr/bin/git\n"),
    )

    plan = release_safety.uninstall_plan_for_detection(
        detection,
        system={"distribution_id": "ubuntu", "package_managers": []},
    )

    assert plan is not None
    assert plan.manager == "apt"
    assert plan.package_name == "git"
    assert plan.command == ("sudo", "apt", "remove", "git")


def test_uninstall_fails_closed_when_owner_does_not_match_catalog(monkeypatch: object) -> None:
    detection = _detection(package_manager="dpkg", packages={"apt": "git"})

    monkeypatch.setattr(
        release_safety,
        "run_command",
        lambda command, timeout=4: _result(tuple(command), "git-core: /usr/bin/git\n"),
    )

    plan = release_safety.uninstall_plan_for_detection(
        detection,
        system={"distribution_id": "ubuntu", "package_managers": []},
    )

    assert plan is None


def test_atomic_rpm_ownership_is_not_treated_as_layering_proof(monkeypatch: object) -> None:
    detection = _detection(package_manager="rpm", packages={"dnf": "git"})

    monkeypatch.setattr(
        release_safety,
        "run_command",
        lambda command, timeout=4: _result(tuple(command), "git"),
    )

    plan = release_safety.uninstall_plan_for_detection(
        detection,
        system={
            "distribution_id": "bazzite",
            "package_managers": [{"id": "rpm-ostree", "installed": True}],
        },
    )

    assert plan is None


def test_release_safety_replaces_public_mutating_callbacks() -> None:
    app = typer.Typer()

    @app.command("self-update")
    def legacy_self_update() -> None:
        pass

    @app.command()
    def uninstall() -> None:
        pass

    release_safety.apply_release_safety(app)

    callbacks = {
        release_safety._command_name(command): command.callback
        for command in app.registered_commands
    }
    assert callbacks["self-update"] is release_safety.safe_self_update
    assert callbacks["uninstall"] is release_safety.safe_uninstall
