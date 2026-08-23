"""Executable PATH ownership and version conflict analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import typer

from devdoctor.path_analysis import executable_paths
from devdoctor.utils import parse_version, run_command


@dataclass(frozen=True, slots=True)
class ExecutableInstance:
    executable: str
    path: str
    version: str | None
    owner_manager: str | None
    owner_package: str | None


@dataclass(frozen=True, slots=True)
class ExecutableConflict:
    executable: str
    kind: str
    instances: tuple[ExecutableInstance, ...]


def _owner(path: str) -> tuple[str | None, str | None]:
    probes = (
        ("dpkg", ("dpkg", "-S", path)),
        ("rpm", ("rpm", "-qf", path)),
        ("pacman", ("pacman", "-Qo", path)),
    )
    for manager, command in probes:
        result = run_command(command, timeout=3)
        if result.returncode == 0 and result.combined_output:
            return manager, result.combined_output.splitlines()[0][:160]
    return None, None


def analyze_executable(executable: str) -> ExecutableConflict | None:
    """Return duplicate/version/ownership information for one PATH executable."""

    paths = executable_paths(executable)
    if len(paths) <= 1:
        return None

    instances: list[ExecutableInstance] = []
    for path in paths:
        result = run_command((path, "--version"), timeout=4)
        owner_manager, owner_package = _owner(path)
        instances.append(
            ExecutableInstance(
                executable=executable,
                path=path,
                version=parse_version(result.combined_output),
                owner_manager=owner_manager,
                owner_package=owner_package,
            )
        )

    versions = {instance.version for instance in instances if instance.version}
    owners = {instance.owner_manager for instance in instances if instance.owner_manager}
    if len(versions) > 1:
        kind = "version-shadowing"
    elif len(owners) > 1:
        kind = "ownership-shadowing"
    else:
        kind = "duplicate-path"
    return ExecutableConflict(executable=executable, kind=kind, instances=tuple(instances))


def analyze_executables(executables: Iterable[str]) -> tuple[ExecutableConflict, ...]:
    """Analyze a bounded set of executable names in PATH order."""

    conflicts: list[ExecutableConflict] = []
    for executable in sorted(set(executables)):
        conflict = analyze_executable(executable)
        if conflict is not None:
            conflicts.append(conflict)
    return tuple(conflicts)


def register_path_conflict_command(app: typer.Typer) -> None:
    """Register an explicit, read-only PATH conflict command."""

    @app.command("path-conflicts")
    def path_conflicts(
        executables: list[str] | None = typer.Argument(
            None,
            help="Executable names to inspect. Defaults to common developer runtimes.",
        ),
    ) -> None:
        targets = tuple(executables or ("python", "python3", "node", "npm", "git", "go", "cargo"))
        conflicts = analyze_executables(targets)
        if not conflicts:
            typer.echo("No duplicate PATH executables detected in the selected set.")
            return
        for conflict in conflicts:
            typer.echo(f"{conflict.executable}\t{conflict.kind}")
            for instance in conflict.instances:
                owner = instance.owner_manager or "unowned"
                version = instance.version or "unknown-version"
                typer.echo(f"  {instance.path}\t{version}\t{owner}")
