from __future__ import annotations

from devdoctor import path_conflicts
from devdoctor.utils import CommandResult


def _result(command: tuple[str, ...], output: str, returncode: int = 0) -> CommandResult:
    return CommandResult(
        command=command,
        returncode=returncode,
        stdout=output if returncode == 0 else "",
        stderr=output if returncode != 0 else "",
        duration_seconds=0.001,
    )


def test_detects_version_shadowing(monkeypatch: object) -> None:
    monkeypatch.setattr(
        path_conflicts,
        "executable_paths",
        lambda executable: ("/usr/bin/python", "/home/alice/.local/bin/python"),
    )

    def fake_run(command: tuple[str, ...], timeout: float = 4) -> CommandResult:
        if command == ("/usr/bin/python", "--version"):
            return _result(command, "Python 3.12.9")
        if command == ("/home/alice/.local/bin/python", "--version"):
            return _result(command, "Python 3.13.2")
        if command[0] == "rpm" and command[-1] == "/usr/bin/python":
            return _result(command, "python3-3.12.9-1.fc42.x86_64")
        return _result(command, "not owned", returncode=1)

    monkeypatch.setattr(path_conflicts, "run_command", fake_run)

    conflict = path_conflicts.analyze_executable("python")

    assert conflict is not None
    assert conflict.kind == "version-shadowing"
    assert [instance.version for instance in conflict.instances] == ["3.12.9", "3.13.2"]


def test_detects_ownership_shadowing_with_same_version(monkeypatch: object) -> None:
    monkeypatch.setattr(
        path_conflicts,
        "executable_paths",
        lambda executable: ("/usr/bin/node", "/opt/node/bin/node"),
    )

    def fake_run(command: tuple[str, ...], timeout: float = 4) -> CommandResult:
        if command[-1] == "--version":
            return _result(command, "v22.10.0")
        if command[0] == "dpkg" and command[-1] == "/usr/bin/node":
            return _result(command, "nodejs: /usr/bin/node")
        if command[0] == "rpm" and command[-1] == "/opt/node/bin/node":
            return _result(command, "nodejs-22.10.0-1.x86_64")
        return _result(command, "not owned", returncode=1)

    monkeypatch.setattr(path_conflicts, "run_command", fake_run)

    conflict = path_conflicts.analyze_executable("node")

    assert conflict is not None
    assert conflict.kind == "ownership-shadowing"
