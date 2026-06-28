from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from devdoctor import bootstrap
from devdoctor.bootstrap import (
    BOOTSTRAP_TOOLS,
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
    assert plan.command == ("sudo", "apt", "install", "git")
    assert plan.dry_run_command == ("apt", "install", "--dry-run", "git")


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


def test_profiles_reference_existing_tool_specs() -> None:
    profile = profile_by_id("python")

    assert profile is not None
    assert "ruff" in profile.tool_ids
    assert {spec.id for spec in specs_for_profile(profile)} == set(profile.tool_ids)


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

    assert summary["total"] == 2
    assert summary["installed"] == 1
    assert summary["missing"] == 1
    assert inventory.missing[0].spec.id == "docker"
