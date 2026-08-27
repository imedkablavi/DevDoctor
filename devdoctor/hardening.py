"""Runtime hardening helpers for package-manager policy, diagnostics, and completions."""

from __future__ import annotations

import json
import os
import platform
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import typer

from devdoctor.package_managers import (
    PackageManagerInfo,
    detect_package_managers,
    is_atomic_host,
    package_manager_conflicts,
)
from devdoctor.utils import read_os_release

_REGISTERED_APP_IDS: set[int] = set()
_ATOMIC_USER_SPACE_ORDER = ("brew", "flatpak", "nix", "cargo", "npm", "pnpm", "pipx", "pip")
_ALLOWED_SESSION_TYPES = {"wayland", "x11", "tty"}
_ALLOWED_SHELL_NAMES = {"bash", "zsh", "fish", "sh", "dash", "ksh", "csh", "tcsh", "nu"}


def installed_manager_ids(managers: Iterable[PackageManagerInfo] | None = None) -> set[str]:
    """Return installed package manager IDs from detection results."""

    return {manager.id for manager in (managers or detect_package_managers()) if manager.installed}


def atomic_safe_manager_order(
    release: Mapping[str, str] | None = None,
    managers: Iterable[PackageManagerInfo] | None = None,
) -> tuple[str, ...]:
    """Return a safe preference order that never uses DNF for Atomic host mutations."""

    manager_tuple = tuple(managers or detect_package_managers())
    installed = installed_manager_ids(manager_tuple)
    release_data = dict(release or read_os_release())
    if is_atomic_host(release_data, manager_tuple):
        order = (*_ATOMIC_USER_SPACE_ORDER, "rpm-ostree")
        return tuple(manager for manager in order if manager in installed)

    distro_id = release_data.get("ID", "").lower()
    distro_like = {item.lower() for item in release_data.get("ID_LIKE", "").split()}
    if distro_id in {"ubuntu", "debian", "linuxmint", "pop"} or distro_like.intersection(
        {"debian", "ubuntu"}
    ):
        order = ("apt", "flatpak", "snap", "brew", "nix", "cargo", "npm", "pipx", "pip")
    elif distro_id == "fedora" or "fedora" in distro_like:
        order = ("dnf", "flatpak", "brew", "nix", "cargo", "npm", "pipx", "pip")
    elif distro_id in {"arch", "manjaro"} or "arch" in distro_like:
        order = ("pacman", "yay", "paru", "flatpak", "nix", "cargo", "npm", "pipx", "pip")
    elif distro_id.startswith("opensuse") or "suse" in distro_like:
        order = ("zypper", "flatpak", "brew", "nix", "cargo", "npm", "pipx", "pip")
    else:
        order = ("brew", "nix", "flatpak", "cargo", "npm", "pipx", "pip")
    return tuple(manager for manager in order if manager in installed)


def _manager_ids_from_system(system: Mapping[str, Any]) -> set[str]:
    values = system.get("package_managers", ())
    return {
        str(item.get("id"))
        for item in values
        if isinstance(item, Mapping) and item.get("installed") is True
    }


def _system_context_is_atomic(system: Mapping[str, Any]) -> bool:
    """Use the inventory's persisted classification without launching new probes."""

    if "atomic_host" in system:
        return system.get("atomic_host") is True

    distro_id = str(system.get("distribution_id", "")).lower()
    if distro_id == "bazzite":
        return True

    managers = _manager_ids_from_system(system)
    if "rpm-ostree" not in managers:
        return False

    distribution = str(system.get("distribution", "")).lower()
    atomic_markers = ("silverblue", "kinoite", "sericea", "onyx", "atomic", "ostree")
    if any(marker in distribution for marker in atomic_markers):
        return True
    return distro_id in {"ublue", "universal-blue"}


def _manager_ids_from_inventory(inventory: Any) -> set[str]:
    system = getattr(inventory, "system", {})
    return _manager_ids_from_system(system) if isinstance(system, Mapping) else set()


def _inventory_atomic(inventory: Any) -> bool:
    system = getattr(inventory, "system", {})
    return _system_context_is_atomic(system) if isinstance(system, Mapping) else False


def apply_runtime_hardening() -> None:
    """Patch legacy internal planners with Atomic-safe behavior until they are refactored."""

    from devdoctor import bootstrap, cli

    if getattr(bootstrap, "_devdoctor_hardened", False):
        return

    original_preferred = bootstrap._preferred_install_manager
    original_update_commands = cli._update_commands
    original_cache_commands = cli._cache_clean_commands

    def preferred_install_manager(spec: Any, system: Mapping[str, Any]) -> tuple[str, str] | None:
        installed = _manager_ids_from_system(system)
        if _system_context_is_atomic(system):
            for manager in (*_ATOMIC_USER_SPACE_ORDER, "rpm-ostree"):
                if manager in installed and manager in spec.packages:
                    if manager == "rpm-ostree":
                        reason = (
                            "Atomic/image-based host policy: no mapped user-space manager is "
                            "available, so use explicit rpm-ostree layering and never dnf."
                        )
                    else:
                        reason = (
                            "Atomic/image-based host policy: prefer mapped user-space tooling "
                            "before rpm-ostree layering and never use dnf for host mutation."
                        )
                    return manager, reason
            return None
        return original_preferred(spec, system)

    def update_commands(inventory: Any) -> tuple[tuple[str, ...], ...]:
        if not _inventory_atomic(inventory):
            return original_update_commands(inventory)
        managers = _manager_ids_from_inventory(inventory)
        commands: list[tuple[str, ...]] = []
        if "rpm-ostree" in managers:
            commands.append(("rpm-ostree", "upgrade"))
        if "flatpak" in managers:
            commands.append(("flatpak", "update"))
        if "brew" in managers:
            commands.extend((("brew", "update"), ("brew", "upgrade")))
        return tuple(commands)

    def cache_clean_commands(inventory: Any) -> tuple[tuple[str, ...], ...]:
        commands = original_cache_commands(inventory)
        if not _inventory_atomic(inventory):
            return commands
        return tuple(
            command for command in commands if not (len(command) > 1 and command[1] == "dnf")
        )

    bootstrap._preferred_install_manager = preferred_install_manager
    cli._update_commands = update_commands
    cli._cache_clean_commands = cache_clean_commands
    bootstrap._devdoctor_hardened = True


def _redact_string(value: str) -> str:
    home = str(Path.home())
    redacted = value.replace(home, "~") if home else value
    redacted = re.sub(r"/home/[^/\s]+", "/home/<user>", redacted)
    redacted = re.sub(r"/Users/[^/\s]+", "/Users/<user>", redacted)
    redacted = re.sub(
        r"(?i)(token|secret|password|passwd|api[_-]?key)=([^\s]+)", r"\1=<redacted>", redacted
    )
    return redacted


def _path_class(path: str | None) -> str | None:
    if not path:
        return None
    normalized = path.lower()
    if ".linuxbrew" in normalized or "/homebrew/" in normalized:
        return "homebrew"
    if (
        normalized.startswith("/usr/")
        or normalized.startswith("/bin/")
        or normalized.startswith("/sbin/")
    ):
        return "system"
    if normalized.startswith(str(Path.home()).lower()):
        return "user"
    if normalized.startswith("/nix/"):
        return "nix"
    return "other"


def _normalized_session_type() -> str:
    value = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
    return value if value in _ALLOWED_SESSION_TYPES else "unknown"


def _normalized_shell_name() -> str:
    value = Path(os.environ.get("SHELL", "")).name.strip().lower()
    return value if value in _ALLOWED_SHELL_NAMES else "unknown"


def safe_diagnostic_snapshot() -> dict[str, Any]:
    """Build a richer diagnostic bundle without usernames, hostnames, env secrets, or raw PATH."""

    release = read_os_release()
    managers = detect_package_managers(include_versions=True)
    conflicts = package_manager_conflicts(managers, release)
    return {
        "schema_version": 1,
        "platform": {
            "distribution": _redact_string(release.get("PRETTY_NAME", "unknown")),
            "distribution_id": release.get("ID", "unknown"),
            "variant_id": release.get("VARIANT_ID", ""),
            "architecture": platform.machine() or "unknown",
            "kernel": platform.release(),
            "python": platform.python_version(),
            "session_type": _normalized_session_type(),
            "shell": _normalized_shell_name(),
            "atomic_host": is_atomic_host(release, managers),
        },
        "package_managers": [
            {
                "id": manager.id,
                "installed": manager.installed,
                "version": manager.version,
                "path_class": _path_class(manager.path),
                "family": manager.family,
            }
            for manager in managers
        ],
        "manager_conflicts": [
            {
                "kind": conflict.kind,
                "managers": list(conflict.managers),
                "severity": conflict.severity,
                "message": conflict.message,
            }
            for conflict in conflicts
        ],
        "path": {
            "entry_count": len(
                [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
            ),
            "contains_empty_entry": "" in os.environ.get("PATH", "").split(os.pathsep),
        },
        "privacy": {
            "hostname_included": False,
            "username_included": False,
            "environment_values_included": False,
            "raw_path_included": False,
        },
    }


def _registered_name(item: Any) -> str | None:
    explicit = getattr(item, "name", None)
    if explicit:
        return str(explicit)
    callback = getattr(item, "callback", None)
    callback_name = getattr(callback, "__name__", "")
    return callback_name.replace("_", "-") if callback_name else None


def top_level_command_names(app: typer.Typer) -> tuple[str, ...]:
    """Return the commands/groups Typer will actually expose at invocation time."""

    names = {
        name
        for item in (*app.registered_commands, *app.registered_groups)
        if (name := _registered_name(item))
    }
    return tuple(sorted(names))


def completion_script(shell: str, commands: Sequence[str], tools: Sequence[str]) -> str:
    """Generate deterministic top-level Bash/Zsh/Fish completions without shell profile mutation."""

    normalized = shell.lower()
    command_words = " ".join(sorted(set(commands)))
    tool_words = " ".join(sorted(set(tools)))
    if normalized == "bash":
        return f"""_devdoctor_complete() {{
  local cur prev
  COMPREPLY=()
  cur="${{COMP_WORDS[COMP_CWORD]}}"
  prev="${{COMP_WORDS[COMP_CWORD-1]}}"
  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "{command_words}" -- "$cur") )
  else
    case "$prev" in
      check|install|repair|repair-apply|verify|uninstall)
        COMPREPLY=( $(compgen -W "{tool_words}" -- "$cur") )
        ;;
    esac
  fi
}}
complete -F _devdoctor_complete devdoctor
"""
    if normalized == "zsh":
        return f"""#compdef devdoctor
_devdoctor() {{
  local -a commands tools
  commands=({command_words})
  tools=({tool_words})
  if (( CURRENT == 2 )); then
    _describe 'command' commands
  else
    case $words[2] in
      check|install|repair|repair-apply|verify|uninstall) _describe 'tool' tools ;;
    esac
  fi
}}
compdef _devdoctor devdoctor
"""
    if normalized == "fish":
        lines = ["complete -c devdoctor -f"]
        for command in sorted(set(commands)):
            lines.append(f"complete -c devdoctor -n '__fish_use_subcommand' -a '{command}'")
        for command in ("check", "install", "repair", "repair-apply", "verify", "uninstall"):
            lines.append(
                f"complete -c devdoctor -n '__fish_seen_subcommand_from {command}' "
                f"-a '{tool_words}'"
            )
        return "\n".join(lines) + "\n"
    raise ValueError("shell must be one of: bash, zsh, fish")


def benchmark_local_scan(iterations: int = 3) -> dict[str, Any]:
    """Benchmark local startup-adjacent imports and a bounded inventory scan."""

    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    from devdoctor.bootstrap import bootstrap_inventory

    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        bootstrap_inventory(include_ids=("git", "python", "node"))
        samples.append(time.perf_counter() - started)
    return {
        "iterations": iterations,
        "samples_seconds": [round(sample, 4) for sample in samples],
        "min_seconds": round(min(samples), 4),
        "max_seconds": round(max(samples), 4),
        "mean_seconds": round(sum(samples) / len(samples), 4),
    }


def register_hardening_commands(app: typer.Typer) -> None:
    """Register release-hardening commands once on the public Typer app."""

    if id(app) in _REGISTERED_APP_IDS:
        return
    _REGISTERED_APP_IDS.add(id(app))

    @app.command("completion")
    def completion(
        shell: str = typer.Argument(..., help="Shell name: bash, zsh, or fish."),
    ) -> None:
        """Print a completion script; DevDoctor never edits shell profiles automatically."""

        from devdoctor.bootstrap import get_bootstrap_tools

        commands = top_level_command_names(app)
        tools = tuple(spec.id for spec in get_bootstrap_tools())
        try:
            typer.echo(completion_script(shell, commands, tools), nl=False)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    @app.command("diagnostics")
    def diagnostics(
        output: Path = typer.Option(Path("devdoctor-diagnostics.json"), "--output", "-o"),
        stdout: bool = typer.Option(
            False, "--stdout", help="Print JSON instead of writing a file."
        ),
    ) -> None:
        """Export a privacy-scrubbed diagnostic snapshot."""

        payload = json.dumps(safe_diagnostic_snapshot(), indent=2, sort_keys=True) + "\n"
        if stdout:
            typer.echo(payload, nl=False)
            return
        output.write_text(payload, encoding="utf-8")
        typer.echo(str(output))

    @app.command("manager-conflicts")
    def manager_conflicts() -> None:
        """Report package-manager overlap and Atomic-host policy conflicts."""

        managers = detect_package_managers()
        conflicts = package_manager_conflicts(managers, read_os_release())
        if not conflicts:
            typer.echo("No package-manager conflicts detected.")
            return
        for conflict in conflicts:
            typer.echo(f"{conflict.severity}\t{conflict.kind}\t{conflict.message}")

    @app.command("benchmark")
    def benchmark(iterations: int = typer.Option(3, "--iterations", min=1, max=20)) -> None:
        """Measure bounded local scan performance without applying changes."""

        typer.echo(json.dumps(benchmark_local_scan(iterations), indent=2, sort_keys=True))
