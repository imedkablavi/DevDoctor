from __future__ import annotations

import json
from pathlib import Path

import pytest

from devdoctor import hardening, package_managers

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "package_manager_cases.json"


def _manager(manager_id: str, *, installed: bool) -> package_managers.PackageManagerInfo:
    definitions = {item[0]: item for item in package_managers.PACKAGE_MANAGERS}
    _, title, executable, family, command_hint = definitions[manager_id]
    return package_managers.PackageManagerInfo(
        id=manager_id,
        title=title,
        executable=executable,
        installed=installed,
        path=f"/usr/bin/{executable}" if installed else None,
        family=family,
        version="1.0" if installed else None,
        command_hint=command_hint,
    )


def _fixture_cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _fixture_cases(), ids=lambda case: str(case["name"]))
def test_package_manager_fixture_matrix(case: dict[str, object]) -> None:
    installed = set(case["installed"])
    manager_ids = {definition[0] for definition in package_managers.PACKAGE_MANAGERS}
    managers = tuple(
        _manager(manager_id, installed=manager_id in installed) for manager_id in manager_ids
    )
    release = case["release"]

    assert package_managers.is_atomic_host(release, managers) is case["expected_atomic"]
    order = hardening.atomic_safe_manager_order(release, managers)
    assert order[0] == case["expected_primary"]

    conflicts = {
        conflict.kind
        for conflict in package_managers.package_manager_conflicts(managers, release)
    }
    assert conflicts == set(case["expected_conflicts"])


def test_atomic_manager_order_never_returns_dnf() -> None:
    managers = (
        _manager("dnf", installed=True),
        _manager("rpm-ostree", installed=True),
        _manager("flatpak", installed=True),
    )
    release = {"ID": "fedora", "VARIANT_ID": "kinoite", "OSTREE_VERSION": "43.1"}

    order = hardening.atomic_safe_manager_order(release, managers)

    assert "rpm-ostree" in order
    assert "dnf" not in order


def test_install_plan_for_silverblue_uses_rpm_ostree_not_dnf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "fedora", "VARIANT_ID": "silverblue", "OSTREE_VERSION": "43.1"},
    )
    monkeypatch.setattr(
        package_managers.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"dnf", "rpm-ostree", "flatpak"} else None,
    )

    plan = package_managers.install_plan_for_tool("tool.git", "Git")

    assert plan is not None
    assert plan.manager == "rpm-ostree"
    assert plan.command == "rpm-ostree install git"
    assert "dnf" not in plan.command


def test_install_plan_for_opensuse_uses_zypper(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "opensuse-tumbleweed", "ID_LIKE": "suse opensuse"},
    )
    monkeypatch.setattr(package_managers.shutil, "which", lambda name: None)

    plan = package_managers.install_plan_for_tool("tool.git", "Git")

    assert plan is not None
    assert plan.manager == "Zypper"
    assert plan.command == "sudo zypper install git"


def test_completion_scripts_cover_all_supported_shells() -> None:
    commands = ("check", "install", "repair")
    tools = ("git", "python")

    assert "complete -F" in hardening.completion_script("bash", commands, tools)
    assert "compdef" in hardening.completion_script("zsh", commands, tools)
    assert "complete -c devdoctor" in hardening.completion_script("fish", commands, tools)


def test_safe_diagnostics_do_not_include_raw_home_or_environment_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/home/alice/.local/bin:/usr/bin")
    monkeypatch.setenv("API_TOKEN", "super-secret-value")
    monkeypatch.setattr(
        hardening,
        "read_os_release",
        lambda: {"ID": "ubuntu", "PRETTY_NAME": "Ubuntu"},
    )
    monkeypatch.setattr(
        hardening,
        "detect_package_managers",
        lambda: (_manager("apt", installed=True),),
    )

    snapshot = hardening.safe_diagnostic_snapshot()
    rendered = json.dumps(snapshot)

    assert "/home/alice/.local/bin" not in rendered
    assert "super-secret-value" not in rendered
    assert snapshot["privacy"]["raw_path_included"] is False
    assert snapshot["privacy"]["environment_values_included"] is False
