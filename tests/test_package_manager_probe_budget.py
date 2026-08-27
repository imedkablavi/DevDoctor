from __future__ import annotations

from devdoctor import package_managers


def test_default_manager_detection_does_not_spawn_version_probes(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers.shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name in {"apt", "npm", "pnpm"} else None,
    )

    def forbidden_probe(*args: object, **kwargs: object) -> object:
        raise AssertionError("default manager detection must not spawn version subprocesses")

    monkeypatch.setattr(package_managers, "run_command", forbidden_probe)

    managers = package_managers.detect_package_managers()
    installed = {manager.id: manager for manager in managers if manager.installed}

    assert set(installed) == {"apt", "npm", "pnpm"}
    assert all(manager.version is None for manager in installed.values())


def test_manager_version_probes_remain_available_when_requested(monkeypatch: object) -> None:
    monkeypatch.setattr(
        package_managers.shutil,
        "which",
        lambda name: "/usr/bin/pnpm" if name == "pnpm" else None,
    )
    calls: list[tuple[str, ...]] = []

    def runner(command: object, timeout: float = 3) -> object:
        from devdoctor.utils import CommandResult

        normalized = tuple(command)  # type: ignore[arg-type]
        calls.append(normalized)
        return CommandResult(
            command=normalized,
            returncode=0,
            stdout="pnpm 10.4.1\n",
            stderr="",
            duration_seconds=0.01,
        )

    monkeypatch.setattr(package_managers, "run_command", runner)

    managers = package_managers.detect_package_managers(include_versions=True)
    pnpm = next(manager for manager in managers if manager.id == "pnpm")

    assert pnpm.version == "10.4.1"
    assert calls == [("/usr/bin/pnpm", "--version")]
