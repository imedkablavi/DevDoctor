from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from devdoctor import bootstrap
from devdoctor.bootstrap import (
    BOOTSTRAP_TOOLS,
    HealthState,
    ToolSpec,
    detect_tool,
    install_plan_for_spec,
    profile_by_id,
    specs_for_profile,
)
from devdoctor.package_managers import PackageManagerInfo
from devdoctor.utils import CommandResult


def test_install_plan_uses_detected_apt_manager() -> None:
    spec = next(item for item in BOOTSTRAP_TOOLS if item.id == "git")
    system = {
        "distribution_id": "ubuntu",
        "distribution_like": ["debian"],
        "package_managers": [{"id": "apt", "installed": True}],
    }

    plan = install_plan_for_spec(spec, system=system)

    assert plan is not None
    assert plan.manager == "apt"
    assert "native package manager" in plan.manager_reason
    assert plan.command == ("sudo", "apt", "install", "git")
    assert plan.dry_run_command == ("apt", "install", "--dry-run", "git")
    assert plan.requires_sudo is True


def test_detect_tool_reports_installed_version_and_path(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    executable = tmp_path / "example"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    spec = ToolSpec(
        id="example",
        title="Example",
        category=bootstrap.BootstrapCategory.TERMINAL_UTILITIES,
        executable="example",
    )

    def which(name: str) -> str | None:
        return str(executable) if name == "example" else None

    def runner(command: Sequence[str], timeout: float = 5.0) -> CommandResult:
        return CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="example 2.4.6\n",
            stderr="",
            duration_seconds=0.01,
        )

    monkeypatch.setattr(bootstrap.shutil, "which", which)
    monkeypatch.setattr(bootstrap, "run_command", runner)

    detection = detect_tool(spec, system={"package_managers": []})

    assert detection.installed is True
    assert detection.version == "2.4.6"
    assert detection.executable_path == str(executable)
    assert detection.broken_installation is False


def test_detect_tool_reports_non_executable_path_problem(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "broken-tool"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o644)
    spec = ToolSpec(
        id="broken-tool",
        title="Broken Tool",
        category=bootstrap.BootstrapCategory.TERMINAL_UTILITIES,
        executable="broken-tool",
    )

    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)

    detection = detect_tool(spec, system={"package_managers": []})

    assert detection.installed is False
    assert detection.broken_installation is True
    assert detection.executable_path == str(executable)
    assert detection.permission_issues


def test_detect_tool_reports_docker_compose_cli_plugin(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\n", encoding="utf-8")
    docker.chmod(0o755)
    spec = next(item for item in BOOTSTRAP_TOOLS if item.id == "docker-compose")

    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: str(docker) if name == "docker" else None,
    )
    monkeypatch.setattr(
        bootstrap,
        "run_command",
        lambda command, timeout=5.0: CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="Docker Compose version v2.29.2\n",
            stderr="",
            duration_seconds=0.01,
        ),
    )

    detection = detect_tool(spec, system={"package_managers": []})
    plan = install_plan_for_spec(
        spec,
        system={
            "distribution_id": "ubuntu",
            "distribution_like": ["debian"],
            "package_managers": [{"id": "apt", "installed": True}],
        },
    )

    assert detection.installed is True
    assert detection.version == "2.29.2"
    assert detection.installation_method == "docker CLI plugin"
    assert plan is not None
    assert plan.verify_command == ("docker", "compose", "version")


def test_profiles_reference_existing_tool_specs() -> None:
    profile = profile_by_id("python")

    assert profile is not None
    assert "ruff" in profile.tool_ids
    assert {spec.id for spec in specs_for_profile(profile)} == set(profile.tool_ids)


def test_scoped_inventory_expands_optional_dependencies_only_when_requested(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(bootstrap, "read_os_release", lambda: {"ID": "ubuntu"})
    monkeypatch.setattr(bootstrap, "detect_package_managers", lambda: ())
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)

    required_only = bootstrap.bootstrap_inventory(include_ids=("git",))
    with_optional = bootstrap.bootstrap_inventory(
        include_ids=("git",),
        include_optional_dependencies=True,
    )

    assert {item.spec.id for item in required_only.detections} == {"git", "ssh"}
    assert {item.spec.id for item in with_optional.detections} == {"git", "gpg", "ssh"}


def test_bootstrap_inventory_summary(monkeypatch: object) -> None:
    monkeypatch.setattr(bootstrap, "read_os_release", lambda: {"ID": "ubuntu"})
    monkeypatch.setattr(
        bootstrap,
        "detect_package_managers",
        lambda: (
            PackageManagerInfo(
                id="apt",
                title="APT",
                executable="apt",
                installed=True,
                path="/usr/bin/apt",
                family="system",
                version="2.8.0",
                command_hint="sudo apt install <package>",
            ),
        ),
    )
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: "/usr/bin/git" if name == "git" else None,
    )
    monkeypatch.setattr(
        bootstrap,
        "run_command",
        lambda command, timeout=5.0: CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="git version 2.45.0\n",
            stderr="",
            duration_seconds=0.01,
        ),
    )

    inventory = bootstrap.bootstrap_inventory(include_ids=("git", "docker"))
    summary = inventory.to_dict()["summary"]

    assert summary["total"] == 5
    assert summary["installed"] == 1
    assert summary["missing"] == 4
    assert summary["warnings"] == 1
    assert summary["broken"] == 0
    assert {item.spec.id for item in inventory.missing} == {
        "docker",
        "docker-buildx",
        "docker-compose",
        "ssh",
    }


def test_dependency_resolution_reports_missing_required_tools(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    flutter = tmp_path / "flutter"
    flutter.write_text("#!/bin/sh\n", encoding="utf-8")
    flutter.chmod(0o755)
    monkeypatch.setattr(bootstrap, "read_os_release", lambda: {"ID": "ubuntu"})
    monkeypatch.setattr(bootstrap, "detect_package_managers", lambda: ())
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: str(flutter) if name == "flutter" else None,
    )
    monkeypatch.setattr(
        bootstrap,
        "run_command",
        lambda command, timeout=5.0: CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="Flutter 3.24.0\n",
            stderr="",
            duration_seconds=0.01,
        ),
    )

    inventory = bootstrap.bootstrap_inventory(include_ids=("flutter",))
    detection = next(item for item in inventory.detections if item.spec.id == "flutter")

    assert detection.health is HealthState.WARNING
    missing_ids = {status.tool_id for status in detection.dependency_status if not status.installed}
    assert {"git", "java", "adb", "android-sdkmanager"}.issubset(missing_ids)
    assert any(
        "Flutter Android toolchain" in item.problem for item in detection.repair_recommendations
    )


def test_docker_daemon_failure_creates_repair_recommendation(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\n", encoding="utf-8")
    docker.chmod(0o755)
    monkeypatch.setattr(bootstrap, "read_os_release", lambda: {"ID": "fedora"})
    monkeypatch.setattr(bootstrap, "detect_package_managers", lambda: ())
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: str(docker) if name == "docker" else None,
    )

    def runner(command: Sequence[str], timeout: float = 5.0) -> CommandResult:
        if tuple(command)[-1] == "info":
            return CommandResult(
                command=tuple(command),
                returncode=1,
                stdout="",
                stderr="Cannot connect to the Docker daemon",
                duration_seconds=0.01,
            )
        return CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="Docker version 29.0.0\n",
            stderr="",
            duration_seconds=0.01,
        )

    monkeypatch.setattr(bootstrap, "run_command", runner)

    inventory = bootstrap.bootstrap_inventory(include_ids=("docker",))
    detection = next(item for item in inventory.detections if item.spec.id == "docker")

    assert detection.health is HealthState.WARNING
    assert any("Docker daemon" in item.problem for item in detection.repair_recommendations)


def test_missing_primary_tool_does_not_emit_dependency_repairs(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(bootstrap, "read_os_release", lambda: {"ID": "ubuntu"})
    monkeypatch.setattr(bootstrap, "detect_package_managers", lambda: ())
    monkeypatch.setattr(bootstrap.shutil, "which", lambda _name: None)

    inventory = bootstrap.bootstrap_inventory(include_ids=("docker",))
    detection = next(item for item in inventory.detections if item.spec.id == "docker")

    assert detection.installed is False
    assert detection.repair_recommendations == ()
