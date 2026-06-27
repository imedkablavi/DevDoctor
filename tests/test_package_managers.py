from __future__ import annotations

from devdoctor import package_managers
from devdoctor.utils import CommandResult


def test_install_plan_uses_apt_for_ubuntu(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "ubuntu", "ID_LIKE": "debian"},
    )
    monkeypatch.setattr(package_managers.shutil, "which", lambda name: None)

    plan = package_managers.install_plan_for_tool("tool.docker", "Docker")

    assert plan is not None
    assert plan.manager == "APT"
    assert plan.command == "sudo apt install docker.io"


def test_install_plan_prefers_homebrew_on_bazzite(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "bazzite", "ID_LIKE": "fedora"},
    )
    monkeypatch.setattr(
        package_managers.shutil,
        "which",
        lambda name: "/home/linuxbrew/.linuxbrew/bin/brew" if name == "brew" else None,
    )

    plan = package_managers.install_plan_for_tool("tool.node", "Node.js")

    assert plan is not None
    assert plan.manager == "Homebrew"
    assert plan.command == "brew install node"


def test_install_plan_uses_rpm_ostree_on_bazzite_without_homebrew(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "bazzite", "ID_LIKE": "fedora"},
    )
    monkeypatch.setattr(package_managers.shutil, "which", lambda name: None)

    plan = package_managers.install_plan_for_tool("tool.podman", "Podman")

    assert plan is not None
    assert plan.manager == "rpm-ostree"
    assert plan.command == "rpm-ostree install podman"


def test_install_plan_uses_dnf_for_fedora(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "fedora", "ID_LIKE": ""},
    )
    monkeypatch.setattr(package_managers.shutil, "which", lambda name: None)

    plan = package_managers.install_plan_for_tool("tool.go", "Go")

    assert plan is not None
    assert plan.manager == "DNF"
    assert plan.command == "sudo dnf install golang"


def test_install_plan_uses_pacman_for_arch_like_distros(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "manjaro", "ID_LIKE": "arch"},
    )
    monkeypatch.setattr(package_managers.shutil, "which", lambda name: None)

    plan = package_managers.install_plan_for_tool("tool.helm", "Helm")

    assert plan is not None
    assert plan.manager == "Pacman"
    assert plan.command == "sudo pacman -S helm"


def test_install_plan_uses_apt_for_supported_debian_like_distros(monkeypatch: object) -> None:
    for distro_id in ("debian", "linuxmint", "pop"):
        monkeypatch.setattr(
            package_managers,
            "read_os_release",
            lambda distro_id=distro_id: {"ID": distro_id, "ID_LIKE": "debian"},
        )
        monkeypatch.setattr(package_managers.shutil, "which", lambda name: None)

        plan = package_managers.install_plan_for_tool("tool.git", "Git")

        assert plan is not None
        assert plan.manager == "APT"
        assert plan.command == "sudo apt install git"


def test_install_plan_includes_python_runtime(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers,
        "read_os_release",
        lambda: {"ID": "linuxmint", "ID_LIKE": "ubuntu debian"},
    )
    monkeypatch.setattr(package_managers.shutil, "which", lambda name: None)

    plan = package_managers.install_plan_for_tool("tool.python", "Python")

    assert plan is not None
    assert plan.manager == "APT"
    assert plan.command == "sudo apt install python3 python3-pip"


def test_detect_package_managers_includes_version_and_command_hint(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        package_managers.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name == "pnpm" else None,
    )
    monkeypatch.setattr(
        package_managers,
        "run_command",
        lambda command, timeout=3: CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="pnpm 10.4.1\n",
            stderr="",
            duration_seconds=0.01,
        ),
    )

    managers = package_managers.detect_package_managers()
    pnpm = next(manager for manager in managers if manager.id == "pnpm")

    assert pnpm.installed is True
    assert pnpm.version == "10.4.1"
    assert pnpm.command_hint == "pnpm add <package>"
