"""Developer workstation bootstrap inventory and install planning."""

from __future__ import annotations

import os
import shutil
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path

from devdoctor.models import JsonValue
from devdoctor.package_managers import detect_package_managers
from devdoctor.utils import parse_version, read_os_release, run_command

BOOTSTRAP_TOOL_ENTRY_POINT_GROUP = "devdoctor.bootstrap_tools"


class BootstrapCategory(StrEnum):
    """Developer workstation bootstrap categories."""

    SYSTEM = "System"
    PROGRAMMING_LANGUAGES = "Programming Languages"
    VERSION_MANAGERS = "Version Managers"
    PACKAGE_MANAGERS = "Package Managers"
    EDITORS = "Editors"
    CONTAINERS = "Containers"
    VIRTUALIZATION = "Virtualization"
    DATABASES = "Databases"
    CLOUD_CLIS = "Cloud CLIs"
    DEVOPS = "DevOps"
    AI = "AI"
    SECURITY = "Security"
    NETWORKING = "Networking"
    TERMINAL_UTILITIES = "Terminal Utilities"
    BUILD_SYSTEMS = "Build Systems"
    PACKAGE_REGISTRIES = "Package Registries"
    MOBILE_DEVELOPMENT = "Mobile Development"
    GAME_DEVELOPMENT = "Game Development"
    COMPILERS = "Compilers"
    DEBUGGERS = "Debuggers"
    REVERSE_ENGINEERING = "Reverse Engineering"
    MONITORING = "Monitoring"
    SHELL_ENHANCEMENTS = "Shell Enhancements"
    FONTS = "Fonts"
    GIT_UTILITIES = "Git Utilities"
    SSH = "SSH"
    GPG = "GPG"
    SYSTEM_SERVICES = "System Services"


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Catalog metadata for one developer workstation tool."""

    id: str
    title: str
    category: BootstrapCategory
    executable: str
    version_args: tuple[str, ...] = ("--version",)
    website: str = ""
    packages: Mapping[str, str] = field(default_factory=dict)
    config_paths: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    recommended_version: str | None = None


@dataclass(frozen=True, slots=True)
class ToolDetection:
    """Actual detection result for one tool."""

    spec: ToolSpec
    installed: bool
    executable_path: str | None
    version: str | None
    package_manager: str | None
    package_name: str | None
    config_locations: tuple[str, ...]
    broken_installation: bool
    permission_issues: tuple[str, ...]
    path_issues: tuple[str, ...]
    missing_dependencies: tuple[str, ...]
    install_plan: InstallPlan | None

    def to_dict(self) -> dict[str, JsonValue]:
        """Convert the detection result to JSON data."""

        return {
            "id": self.spec.id,
            "title": self.spec.title,
            "category": self.spec.category.value,
            "installed": self.installed,
            "version": self.version,
            "executable": self.spec.executable,
            "path": self.executable_path,
            "package_manager": self.package_manager,
            "package_name": self.package_name,
            "config_locations": list(self.config_locations),
            "official_website": self.spec.website,
            "recommended_version": self.spec.recommended_version,
            "broken_installation": self.broken_installation,
            "permission_issues": list(self.permission_issues),
            "path_issues": list(self.path_issues),
            "missing_dependencies": list(self.missing_dependencies),
            "install_plan": self.install_plan.to_dict() if self.install_plan else None,
        }


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """Safe install plan for a missing bootstrap tool."""

    tool_id: str
    tool_title: str
    manager: str
    command: tuple[str, ...]
    explanation: str
    risk: str
    dry_run_command: tuple[str, ...] | None = None
    verify_command: tuple[str, ...] = ()
    rollback_command: tuple[str, ...] | None = None

    @property
    def command_text(self) -> str:
        """Return a shell-display version of the command."""

        return " ".join(self.command)

    def to_dict(self) -> dict[str, JsonValue]:
        """Convert the install plan to JSON data."""

        return {
            "tool_id": self.tool_id,
            "tool_title": self.tool_title,
            "manager": self.manager,
            "command": list(self.command),
            "command_text": self.command_text,
            "explanation": self.explanation,
            "risk": self.risk,
            "dry_run_command": list(self.dry_run_command) if self.dry_run_command else None,
            "verify_command": list(self.verify_command),
            "rollback_command": list(self.rollback_command) if self.rollback_command else None,
        }


@dataclass(frozen=True, slots=True)
class BootstrapProfile:
    """Named workstation setup profile."""

    id: str
    title: str
    description: str
    tool_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BootstrapInventory:
    """Full bootstrap inventory for the local workstation."""

    system: Mapping[str, JsonValue]
    detections: tuple[ToolDetection, ...]
    profiles: tuple[BootstrapProfile, ...]

    @property
    def missing(self) -> tuple[ToolDetection, ...]:
        """Return tools that were not detected."""

        return tuple(detection for detection in self.detections if not detection.installed)

    @property
    def broken(self) -> tuple[ToolDetection, ...]:
        """Return tools with detected local problems."""

        return tuple(
            detection
            for detection in self.detections
            if detection.broken_installation
            or detection.permission_issues
            or detection.path_issues
            or detection.missing_dependencies
        )

    def categories(self) -> Mapping[BootstrapCategory, tuple[ToolDetection, ...]]:
        """Return detections grouped by bootstrap category."""

        grouped: dict[BootstrapCategory, list[ToolDetection]] = defaultdict(list)
        for detection in self.detections:
            grouped[detection.spec.category].append(detection)
        return {category: tuple(items) for category, items in grouped.items()}

    def to_dict(self) -> dict[str, JsonValue]:
        """Convert the inventory to JSON data."""

        return {
            "system": self.system,
            "summary": {
                "total": len(self.detections),
                "installed": sum(1 for detection in self.detections if detection.installed),
                "missing": len(self.missing),
                "broken": len(self.broken),
            },
            "tools": [detection.to_dict() for detection in self.detections],
            "profiles": [
                {
                    "id": profile.id,
                    "title": profile.title,
                    "description": profile.description,
                    "tool_ids": list(profile.tool_ids),
                }
                for profile in self.profiles
            ],
        }


def bootstrap_inventory(*, include_ids: Iterable[str] | None = None) -> BootstrapInventory:
    """Detect the local workstation bootstrap inventory."""

    specs = get_bootstrap_tools()
    if include_ids is not None:
        wanted = set(include_ids)
        specs = tuple(spec for spec in specs if spec.id in wanted)
    system = detect_system_context()
    detections = tuple(detect_tool(spec, system=system) for spec in specs)
    return BootstrapInventory(system=system, detections=detections, profiles=BOOTSTRAP_PROFILES)


def detect_system_context() -> Mapping[str, JsonValue]:
    """Detect OS, package manager, virtualization, permissions, and PATH context."""

    release = read_os_release()
    distro_id = release.get("ID", "").lower()
    id_like = tuple(item.lower() for item in release.get("ID_LIKE", "").split())
    managers = detect_package_managers()
    path_entries = tuple(entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry)
    return {
        "distribution": release.get("PRETTY_NAME", "unknown"),
        "distribution_id": distro_id or "unknown",
        "distribution_like": list(id_like),
        "architecture": os.uname().machine if hasattr(os, "uname") else "unknown",
        "desktop_environment": _first_env(
            "XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP", "DESKTOP_SESSION"
        ),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown") or "unknown",
        "shell": Path(os.environ.get("SHELL", "")).name or "unknown",
        "terminal": _first_env("TERM_PROGRAM", "TERMINAL", "TERM"),
        "is_root": os.geteuid() == 0 if hasattr(os, "geteuid") else False,
        "can_sudo": shutil.which("sudo") is not None,
        "is_wsl": _is_wsl(),
        "is_container": _is_container(),
        "virtualization": _virtualization(),
        "path_entries": list(path_entries),
        "path_issue_count": sum(1 for entry in path_entries if not Path(entry).exists()),
        "package_managers": [
            {
                "id": manager.id,
                "title": manager.title,
                "installed": manager.installed,
                "path": manager.path,
                "version": manager.version,
                "family": manager.family,
                "command_hint": manager.command_hint,
            }
            for manager in managers
        ],
    }


def detect_tool(spec: ToolSpec, *, system: Mapping[str, JsonValue]) -> ToolDetection:
    """Detect one catalog tool using actual local commands and filesystem state."""

    executable_path = shutil.which(spec.executable)
    problem_path, path_issues, lookup_permission_issues = _path_lookup_problem(
        spec.executable, executable_path=executable_path
    )
    path = executable_path or problem_path
    version = _tool_version(executable_path, spec.version_args)
    permission_issues = _permission_issues(path)
    permission_issues = (*lookup_permission_issues, *permission_issues)
    path_issues = (*path_issues, *_path_issues(path))
    config_locations = _existing_config_locations(spec.config_paths)
    package_manager, package_name = _owning_package(path)
    missing_dependencies = tuple(
        dependency for dependency in spec.dependencies if shutil.which(dependency) is None
    )
    broken = bool(path and (permission_issues or path_issues or missing_dependencies))
    installed = executable_path is not None and not path_issues and not permission_issues
    return ToolDetection(
        spec=spec,
        installed=installed,
        executable_path=path,
        version=version,
        package_manager=package_manager,
        package_name=package_name,
        config_locations=config_locations,
        broken_installation=broken,
        permission_issues=permission_issues,
        path_issues=path_issues,
        missing_dependencies=missing_dependencies,
        install_plan=None if installed else install_plan_for_spec(spec, system=system),
    )


def install_plan_for_spec(
    spec: ToolSpec,
    *,
    system: Mapping[str, JsonValue],
) -> InstallPlan | None:
    """Build a safe install plan for one tool on the detected system."""

    manager = _preferred_install_manager(spec, system)
    if manager is None:
        return None
    package = spec.packages.get(manager)
    if package is None:
        return None
    command, dry_run, rollback = _manager_commands(manager, package)
    if command is None:
        return None
    return InstallPlan(
        tool_id=spec.id,
        tool_title=spec.title,
        manager=manager,
        command=command,
        dry_run_command=dry_run,
        verify_command=(spec.executable, *spec.version_args),
        rollback_command=rollback,
        explanation=f"Install {spec.title} using {manager} package `{package}`.",
        risk=_install_risk(manager),
    )


def profile_by_id(profile_id: str) -> BootstrapProfile | None:
    """Return a profile by id."""

    return next((profile for profile in BOOTSTRAP_PROFILES if profile.id == profile_id), None)


def specs_for_profile(profile: BootstrapProfile) -> tuple[ToolSpec, ...]:
    """Return catalog specs for a profile."""

    by_id = {spec.id: spec for spec in get_bootstrap_tools()}
    return tuple(by_id[tool_id] for tool_id in profile.tool_ids if tool_id in by_id)


def get_bootstrap_tools() -> tuple[ToolSpec, ...]:
    """Return built-in and external bootstrap tool specs."""

    by_id: dict[str, ToolSpec] = {spec.id: spec for spec in BOOTSTRAP_TOOLS}
    for spec in _external_tool_specs():
        by_id.setdefault(spec.id, spec)
    return tuple(by_id.values())


def _external_tool_specs() -> tuple[ToolSpec, ...]:
    specs: list[ToolSpec] = []
    for entry_point in _bootstrap_tool_entry_points():
        try:
            loaded = entry_point.load()
            value = loaded() if callable(loaded) else loaded
        except Exception:
            continue
        if isinstance(value, ToolSpec):
            specs.append(value)
            continue
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
            specs.extend(item for item in value if isinstance(item, ToolSpec))
    return tuple(specs)


def _bootstrap_tool_entry_points() -> tuple[EntryPoint, ...]:
    all_entry_points = entry_points()
    if hasattr(all_entry_points, "select"):
        return tuple(all_entry_points.select(group=BOOTSTRAP_TOOL_ENTRY_POINT_GROUP))
    return tuple(all_entry_points.get(BOOTSTRAP_TOOL_ENTRY_POINT_GROUP, ()))  # type: ignore[union-attr]


def _tool_version(path: str | None, version_args: Sequence[str]) -> str | None:
    if path is None:
        return None
    result = run_command((path, *version_args), timeout=5)
    return parse_version(result.combined_output)


def _permission_issues(path: str | None) -> tuple[str, ...]:
    if path is None:
        return ()
    issues: list[str] = []
    if not os.access(path, os.X_OK):
        issues.append("Executable is not marked executable.")
    if not os.access(path, os.R_OK):
        issues.append("Executable is not readable by the current user.")
    return tuple(issues)


def _path_issues(path: str | None) -> tuple[str, ...]:
    if path is None:
        return ()
    executable = Path(path)
    if executable.is_symlink() and not executable.exists():
        return ("Executable symlink is broken.",)
    return ()


def _path_lookup_problem(
    executable: str,
    *,
    executable_path: str | None,
) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
    if executable_path is not None:
        return (None, (), ())

    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry) / executable
        if not os.path.lexists(candidate):
            continue
        if candidate.is_symlink() and not candidate.exists():
            return (str(candidate), ("Executable symlink is broken.",), ())
        if candidate.exists() and not os.access(candidate, os.X_OK):
            return (
                str(candidate),
                (),
                ("Executable exists in PATH but is not marked executable.",),
            )
    return (None, (), ())


def _existing_config_locations(paths: Iterable[str]) -> tuple[str, ...]:
    home = Path.home()
    existing: list[str] = []
    for raw_path in paths:
        path = Path(raw_path.replace("~", str(home))).expanduser()
        if path.exists():
            existing.append(str(path))
    return tuple(existing)


def _owning_package(path: str | None) -> tuple[str | None, str | None]:
    if path is None:
        return (None, None)
    commands = (
        ("dpkg", ("dpkg", "-S", path)),
        ("rpm", ("rpm", "-qf", path)),
        ("pacman", ("pacman", "-Qo", path)),
    )
    for manager, command in commands:
        if shutil.which(command[0]) is None:
            continue
        result = run_command(command, timeout=3)
        if result.returncode == 0 and result.combined_output:
            return (manager, result.combined_output.splitlines()[0][:160])
    return (None, None)


def _preferred_install_manager(
    spec: ToolSpec,
    system: Mapping[str, JsonValue],
) -> str | None:
    managers = system.get("package_managers", ())
    installed_manager_ids = {
        str(manager.get("id"))
        for manager in managers
        if isinstance(manager, dict) and manager.get("installed") is True
    }
    distro_id = str(system.get("distribution_id", "")).lower()
    distro_like = {str(item).lower() for item in system.get("distribution_like", ())}

    candidates: tuple[str, ...]
    if distro_id == "bazzite":
        candidates = ("brew", "rpm-ostree", "dnf", "flatpak", "cargo", "npm", "pip", "pipx")
    elif distro_id in {"ubuntu", "debian", "linuxmint", "pop"} or distro_like.intersection(
        {"ubuntu", "debian"}
    ):
        candidates = ("apt", "snap", "flatpak", "brew", "cargo", "npm", "pip", "pipx")
    elif distro_id == "fedora" or "fedora" in distro_like:
        candidates = ("dnf", "flatpak", "brew", "cargo", "npm", "pip", "pipx")
    elif distro_id in {"arch", "manjaro"} or "arch" in distro_like:
        candidates = ("pacman", "yay", "paru", "flatpak", "cargo", "npm", "pip", "pipx")
    elif distro_id in {"opensuse", "opensuse-tumbleweed", "sles"} or "suse" in distro_like:
        candidates = ("zypper", "flatpak", "brew", "cargo", "npm", "pip", "pipx")
    elif distro_id == "void":
        candidates = ("xbps", "flatpak", "brew", "cargo", "npm", "pip", "pipx")
    elif distro_id == "alpine":
        candidates = ("apk", "cargo", "npm", "pip", "pipx")
    else:
        candidates = ("brew", "nix", "flatpak", "snap", "cargo", "npm", "pip", "pipx")

    for manager in candidates:
        if manager in installed_manager_ids and manager in spec.packages:
            return manager
    for manager in spec.packages:
        if manager in installed_manager_ids:
            return manager
    return None


def _manager_commands(
    manager: str,
    package: str,
) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None, tuple[str, ...] | None]:
    commands: Mapping[
        str, tuple[tuple[str, ...], tuple[str, ...] | None, tuple[str, ...] | None]
    ] = {
        "apt": (
            ("sudo", "apt", "install", package),
            ("apt", "install", "--dry-run", package),
            ("sudo", "apt", "remove", package),
        ),
        "dnf": (
            ("sudo", "dnf", "install", package),
            ("dnf", "install", "--assumeno", package),
            ("sudo", "dnf", "remove", package),
        ),
        "rpm-ostree": (
            ("rpm-ostree", "install", package),
            None,
            ("rpm-ostree", "uninstall", package),
        ),
        "pacman": (
            ("sudo", "pacman", "-S", package),
            ("pacman", "-Si", package),
            ("sudo", "pacman", "-R", package),
        ),
        "yay": (("yay", "-S", package), ("yay", "-Si", package), ("yay", "-R", package)),
        "paru": (("paru", "-S", package), ("paru", "-Si", package), ("paru", "-R", package)),
        "zypper": (
            ("sudo", "zypper", "install", package),
            ("zypper", "install", "--dry-run", package),
            ("sudo", "zypper", "remove", package),
        ),
        "xbps": (
            ("sudo", "xbps-install", package),
            ("xbps-query", "-Rs", package),
            ("sudo", "xbps-remove", package),
        ),
        "apk": (
            ("sudo", "apk", "add", package),
            ("apk", "info", package),
            ("sudo", "apk", "del", package),
        ),
        "nix": (
            ("nix", "profile", "install", package),
            None,
            ("nix", "profile", "remove", package),
        ),
        "brew": (("brew", "install", package), None, ("brew", "uninstall", package)),
        "flatpak": (
            ("flatpak", "install", "flathub", package),
            ("flatpak", "remote-ls", "flathub", package),
            ("flatpak", "uninstall", package),
        ),
        "snap": (
            ("sudo", "snap", "install", package),
            ("snap", "info", package),
            ("sudo", "snap", "remove", package),
        ),
        "cargo": (("cargo", "install", package), ("cargo", "search", package), None),
        "go": (("go", "install", package), None, None),
        "pip": (
            ("python", "-m", "pip", "install", package),
            None,
            ("python", "-m", "pip", "uninstall", package),
        ),
        "pipx": (("pipx", "install", package), None, ("pipx", "uninstall", package)),
        "npm": (
            ("npm", "install", "-g", package),
            ("npm", "view", package, "version"),
            ("npm", "uninstall", "-g", package),
        ),
        "pnpm": (
            ("pnpm", "add", "-g", package),
            ("pnpm", "view", package, "version"),
            ("pnpm", "remove", "-g", package),
        ),
        "yarn": (
            ("yarn", "global", "add", package),
            ("yarn", "info", package, "version"),
            ("yarn", "global", "remove", package),
        ),
        "gem": (("gem", "install", package), None, ("gem", "uninstall", package)),
        "composer": (
            ("composer", "global", "require", package),
            None,
            ("composer", "global", "remove", package),
        ),
        "sdkman": (("sdk", "install", package), None, ("sdk", "uninstall", package)),
        "rustup": (
            ("rustup", "toolchain", "install", package),
            None,
            ("rustup", "toolchain", "uninstall", package),
        ),
        "flutter": (("flutter", "pub", "global", "activate", package), None, None),
        "mise": (("mise", "use", "-g", package), None, ("mise", "uninstall", package)),
        "asdf": (("asdf", "install", package), None, ("asdf", "uninstall", package)),
    }
    return commands.get(manager, (None, None, None))


def _install_risk(manager: str) -> str:
    if manager in {"apt", "dnf", "pacman", "zypper", "xbps", "apk", "snap"}:
        return "medium - requires system package privileges"
    if manager == "rpm-ostree":
        return "medium - layers an image package and may require reboot"
    if manager in {"pip", "npm", "pnpm", "yarn", "gem", "composer"}:
        return "medium - global language package install"
    return "low - user-space package install"


def _first_env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return "unknown"


def _is_wsl() -> bool:
    try:
        version = Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return "microsoft" in version or "wsl" in version


def _is_container() -> bool:
    if Path("/.dockerenv").exists() or Path("/run/.containerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8").lower()
    except OSError:
        return False
    return any(marker in cgroup for marker in ("docker", "podman", "kubepods", "containerd"))


def _virtualization() -> str:
    if shutil.which("systemd-detect-virt") is None:
        return "unknown"
    result = run_command(("systemd-detect-virt",), timeout=2)
    if result.returncode == 0 and result.combined_output:
        return result.combined_output.splitlines()[0]
    return "none"


def _packages(
    *,
    apt: str | None = None,
    dnf: str | None = None,
    rpm_ostree: str | None = None,
    pacman: str | None = None,
    yay: str | None = None,
    paru: str | None = None,
    zypper: str | None = None,
    xbps: str | None = None,
    apk: str | None = None,
    nix: str | None = None,
    brew: str | None = None,
    flatpak: str | None = None,
    snap: str | None = None,
    cargo: str | None = None,
    go: str | None = None,
    pip: str | None = None,
    pipx: str | None = None,
    npm: str | None = None,
    pnpm: str | None = None,
    yarn: str | None = None,
    gem: str | None = None,
    composer: str | None = None,
    sdkman: str | None = None,
    rustup: str | None = None,
    flutter: str | None = None,
    mise: str | None = None,
    asdf: str | None = None,
) -> Mapping[str, str]:
    values = {
        "apt": apt,
        "dnf": dnf,
        "rpm-ostree": rpm_ostree,
        "pacman": pacman,
        "yay": yay,
        "paru": paru,
        "zypper": zypper,
        "xbps": xbps,
        "apk": apk,
        "nix": nix,
        "brew": brew,
        "flatpak": flatpak,
        "snap": snap,
        "cargo": cargo,
        "go": go,
        "pip": pip,
        "pipx": pipx,
        "npm": npm,
        "pnpm": pnpm,
        "yarn": yarn,
        "gem": gem,
        "composer": composer,
        "sdkman": sdkman,
        "rustup": rustup,
        "flutter": flutter,
        "mise": mise,
        "asdf": asdf,
    }
    return {manager: package for manager, package in values.items() if package}


BOOTSTRAP_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        "git",
        "Git",
        BootstrapCategory.GIT_UTILITIES,
        "git",
        website="https://git-scm.com/",
        config_paths=("~/.gitconfig", "~/.config/git/config"),
        packages=_packages(
            apt="git", dnf="git", pacman="git", zypper="git", xbps="git", apk="git", brew="git"
        ),
    ),
    ToolSpec(
        "curl",
        "curl",
        BootstrapCategory.NETWORKING,
        "curl",
        website="https://curl.se/",
        packages=_packages(
            apt="curl",
            dnf="curl",
            pacman="curl",
            zypper="curl",
            xbps="curl",
            apk="curl",
            brew="curl",
        ),
    ),
    ToolSpec(
        "wget",
        "wget",
        BootstrapCategory.NETWORKING,
        "wget",
        website="https://www.gnu.org/software/wget/",
        packages=_packages(
            apt="wget",
            dnf="wget",
            pacman="wget",
            zypper="wget",
            xbps="wget",
            apk="wget",
            brew="wget",
        ),
    ),
    ToolSpec(
        "python",
        "Python",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "python",
        website="https://python.org/",
        packages=_packages(
            apt="python3",
            dnf="python3",
            pacman="python",
            zypper="python3",
            xbps="python3",
            apk="python3",
            brew="python",
            mise="python@latest",
            asdf="python latest",
        ),
    ),
    ToolSpec(
        "pip",
        "pip",
        BootstrapCategory.PACKAGE_REGISTRIES,
        "pip",
        website="https://pip.pypa.io/",
        packages=_packages(
            apt="python3-pip",
            dnf="python3-pip",
            pacman="python-pip",
            zypper="python3-pip",
            xbps="python3-pip",
            apk="py3-pip",
            brew="python",
        ),
    ),
    ToolSpec(
        "pipx",
        "pipx",
        BootstrapCategory.PACKAGE_REGISTRIES,
        "pipx",
        website="https://pypa.github.io/pipx/",
        packages=_packages(apt="pipx", dnf="pipx", pacman="python-pipx", brew="pipx", pip="pipx"),
    ),
    ToolSpec(
        "node",
        "Node.js",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "node",
        website="https://nodejs.org/",
        packages=_packages(
            apt="nodejs",
            dnf="nodejs",
            pacman="nodejs",
            zypper="nodejs",
            xbps="nodejs",
            apk="nodejs",
            brew="node",
            mise="node@lts",
            asdf="nodejs latest",
        ),
    ),
    ToolSpec(
        "npm",
        "npm",
        BootstrapCategory.PACKAGE_REGISTRIES,
        "npm",
        website="https://www.npmjs.com/",
        config_paths=("~/.npmrc",),
        packages=_packages(
            apt="npm", dnf="npm", pacman="npm", zypper="npm", xbps="nodejs", apk="npm", brew="node"
        ),
    ),
    ToolSpec(
        "pnpm",
        "pnpm",
        BootstrapCategory.PACKAGE_REGISTRIES,
        "pnpm",
        website="https://pnpm.io/",
        config_paths=("~/.npmrc", "~/.config/pnpm/rc"),
        packages=_packages(apt="pnpm", dnf="pnpm", pacman="pnpm", brew="pnpm", npm="pnpm"),
    ),
    ToolSpec(
        "yarn",
        "Yarn",
        BootstrapCategory.PACKAGE_REGISTRIES,
        "yarn",
        website="https://yarnpkg.com/",
        config_paths=("~/.yarnrc", "~/.yarnrc.yml"),
        packages=_packages(apt="yarnpkg", dnf="yarnpkg", pacman="yarn", brew="yarn", npm="yarn"),
    ),
    ToolSpec(
        "bun",
        "Bun",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "bun",
        website="https://bun.sh/",
        config_paths=("~/.bunfig.toml",),
        packages=_packages(brew="bun", npm="bun"),
    ),
    ToolSpec(
        "rustc",
        "Rust",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "rustc",
        website="https://www.rust-lang.org/",
        packages=_packages(
            apt="rustc",
            dnf="rust",
            pacman="rust",
            zypper="rust",
            xbps="rust",
            apk="rust",
            brew="rust",
            rustup="stable",
        ),
    ),
    ToolSpec(
        "cargo",
        "Cargo",
        BootstrapCategory.PACKAGE_REGISTRIES,
        "cargo",
        website="https://doc.rust-lang.org/cargo/",
        config_paths=("~/.cargo/config.toml", "~/.cargo/config"),
        packages=_packages(
            apt="cargo",
            dnf="cargo",
            pacman="cargo",
            zypper="cargo",
            xbps="cargo",
            apk="cargo",
            brew="rust",
        ),
    ),
    ToolSpec(
        "go",
        "Go",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "go",
        version_args=("version",),
        website="https://go.dev/",
        config_paths=("~/.config/go/env",),
        packages=_packages(
            apt="golang-go",
            dnf="golang",
            pacman="go",
            zypper="go",
            xbps="go",
            apk="go",
            brew="go",
            mise="go@latest",
            asdf="golang latest",
        ),
    ),
    ToolSpec(
        "java",
        "Java",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "java",
        version_args=("-version",),
        website="https://openjdk.org/",
        packages=_packages(
            apt="default-jdk",
            dnf="java-latest-openjdk-devel",
            pacman="jdk-openjdk",
            zypper="java-latest-openjdk-devel",
            xbps="openjdk",
            apk="openjdk17",
            brew="openjdk",
            sdkman="java",
        ),
    ),
    ToolSpec(
        "dotnet",
        ".NET",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "dotnet",
        website="https://dotnet.microsoft.com/",
        packages=_packages(
            apt="dotnet-sdk-8.0", dnf="dotnet-sdk-8.0", pacman="dotnet-sdk", brew="dotnet"
        ),
    ),
    ToolSpec(
        "php",
        "PHP",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "php",
        website="https://www.php.net/",
        packages=_packages(
            apt="php-cli",
            dnf="php-cli",
            pacman="php",
            zypper="php8",
            xbps="php",
            apk="php",
            brew="php",
        ),
    ),
    ToolSpec(
        "ruby",
        "Ruby",
        BootstrapCategory.PROGRAMMING_LANGUAGES,
        "ruby",
        website="https://www.ruby-lang.org/",
        packages=_packages(
            apt="ruby",
            dnf="ruby",
            pacman="ruby",
            zypper="ruby",
            xbps="ruby",
            apk="ruby",
            brew="ruby",
            mise="ruby@latest",
            asdf="ruby latest",
        ),
    ),
    ToolSpec(
        "gcc",
        "GCC",
        BootstrapCategory.COMPILERS,
        "gcc",
        website="https://gcc.gnu.org/",
        packages=_packages(
            apt="gcc", dnf="gcc", pacman="gcc", zypper="gcc", xbps="gcc", apk="gcc", brew="gcc"
        ),
    ),
    ToolSpec(
        "clang",
        "Clang",
        BootstrapCategory.COMPILERS,
        "clang",
        website="https://clang.llvm.org/",
        packages=_packages(
            apt="clang",
            dnf="clang",
            pacman="clang",
            zypper="clang",
            xbps="clang",
            apk="clang",
            brew="llvm",
        ),
    ),
    ToolSpec(
        "make",
        "Make",
        BootstrapCategory.BUILD_SYSTEMS,
        "make",
        website="https://www.gnu.org/software/make/",
        packages=_packages(
            apt="make",
            dnf="make",
            pacman="make",
            zypper="make",
            xbps="make",
            apk="make",
            brew="make",
        ),
    ),
    ToolSpec(
        "cmake",
        "CMake",
        BootstrapCategory.BUILD_SYSTEMS,
        "cmake",
        website="https://cmake.org/",
        packages=_packages(
            apt="cmake",
            dnf="cmake",
            pacman="cmake",
            zypper="cmake",
            xbps="cmake",
            apk="cmake",
            brew="cmake",
        ),
    ),
    ToolSpec(
        "ninja",
        "Ninja",
        BootstrapCategory.BUILD_SYSTEMS,
        "ninja",
        website="https://ninja-build.org/",
        packages=_packages(
            apt="ninja-build",
            dnf="ninja-build",
            pacman="ninja",
            zypper="ninja",
            xbps="ninja",
            apk="ninja",
            brew="ninja",
        ),
    ),
    ToolSpec(
        "docker",
        "Docker",
        BootstrapCategory.CONTAINERS,
        "docker",
        website="https://docs.docker.com/engine/",
        config_paths=("~/.docker/config.json", "/etc/docker/daemon.json"),
        packages=_packages(
            apt="docker.io",
            dnf="moby-engine",
            pacman="docker",
            zypper="docker",
            xbps="docker",
            apk="docker",
            brew="docker",
        ),
    ),
    ToolSpec(
        "podman",
        "Podman",
        BootstrapCategory.CONTAINERS,
        "podman",
        website="https://podman.io/",
        config_paths=("~/.config/containers/containers.conf", "/etc/containers/containers.conf"),
        packages=_packages(
            apt="podman",
            dnf="podman",
            rpm_ostree="podman",
            pacman="podman",
            zypper="podman",
            xbps="podman",
            apk="podman",
            brew="podman",
        ),
    ),
    ToolSpec(
        "distrobox",
        "Distrobox",
        BootstrapCategory.CONTAINERS,
        "distrobox",
        website="https://distrobox.it/",
        packages=_packages(
            apt="distrobox",
            dnf="distrobox",
            pacman="distrobox",
            zypper="distrobox",
            xbps="distrobox",
            brew="distrobox",
        ),
    ),
    ToolSpec(
        "kubectl",
        "kubectl",
        BootstrapCategory.DEVOPS,
        "kubectl",
        version_args=("version", "--client=true"),
        website="https://kubernetes.io/docs/tasks/tools/",
        config_paths=("~/.kube/config",),
        packages=_packages(
            apt="kubectl", dnf="kubernetes-client", pacman="kubectl", brew="kubectl", snap="kubectl"
        ),
    ),
    ToolSpec(
        "helm",
        "Helm",
        BootstrapCategory.DEVOPS,
        "helm",
        website="https://helm.sh/",
        config_paths=("~/.config/helm/repositories.yaml",),
        packages=_packages(apt="helm", dnf="helm", pacman="helm", brew="helm", snap="helm"),
    ),
    ToolSpec(
        "terraform",
        "Terraform",
        BootstrapCategory.DEVOPS,
        "terraform",
        website="https://developer.hashicorp.com/terraform",
        config_paths=("~/.terraformrc",),
        packages=_packages(apt="terraform", dnf="terraform", pacman="terraform", brew="terraform"),
    ),
    ToolSpec(
        "ansible",
        "Ansible",
        BootstrapCategory.DEVOPS,
        "ansible",
        website="https://www.ansible.com/",
        config_paths=("~/.ansible.cfg", "/etc/ansible/ansible.cfg"),
        packages=_packages(
            apt="ansible",
            dnf="ansible",
            pacman="ansible",
            zypper="ansible",
            brew="ansible",
            pipx="ansible",
        ),
    ),
    ToolSpec(
        "gh",
        "GitHub CLI",
        BootstrapCategory.CLOUD_CLIS,
        "gh",
        website="https://cli.github.com/",
        config_paths=("~/.config/gh/hosts.yml", "~/.config/gh/config.yml"),
        packages=_packages(apt="gh", dnf="gh", pacman="github-cli", brew="gh"),
    ),
    ToolSpec(
        "aws",
        "AWS CLI",
        BootstrapCategory.CLOUD_CLIS,
        "aws",
        website="https://aws.amazon.com/cli/",
        config_paths=("~/.aws/config", "~/.aws/credentials"),
        packages=_packages(brew="awscli", pipx="awscli", snap="aws-cli"),
    ),
    ToolSpec(
        "az",
        "Azure CLI",
        BootstrapCategory.CLOUD_CLIS,
        "az",
        website="https://learn.microsoft.com/cli/azure/",
        config_paths=("~/.azure/config",),
        packages=_packages(apt="azure-cli", dnf="azure-cli", brew="azure-cli"),
    ),
    ToolSpec(
        "gcloud",
        "Google Cloud CLI",
        BootstrapCategory.CLOUD_CLIS,
        "gcloud",
        website="https://cloud.google.com/sdk",
        config_paths=("~/.config/gcloud/configurations",),
        packages=_packages(brew="google-cloud-sdk", snap="google-cloud-cli"),
    ),
    ToolSpec(
        "code",
        "Visual Studio Code",
        BootstrapCategory.EDITORS,
        "code",
        website="https://code.visualstudio.com/",
        config_paths=("~/.config/Code/User/settings.json",),
        packages=_packages(snap="code", flatpak="com.visualstudio.code", brew="visual-studio-code"),
    ),
    ToolSpec(
        "vim",
        "Vim",
        BootstrapCategory.EDITORS,
        "vim",
        website="https://www.vim.org/",
        config_paths=("~/.vimrc", "~/.vim/vimrc"),
        packages=_packages(
            apt="vim",
            dnf="vim-enhanced",
            pacman="vim",
            zypper="vim",
            xbps="vim",
            apk="vim",
            brew="vim",
        ),
    ),
    ToolSpec(
        "nvim",
        "Neovim",
        BootstrapCategory.EDITORS,
        "nvim",
        website="https://neovim.io/",
        config_paths=("~/.config/nvim/init.lua", "~/.config/nvim/init.vim"),
        packages=_packages(
            apt="neovim",
            dnf="neovim",
            pacman="neovim",
            zypper="neovim",
            xbps="neovim",
            apk="neovim",
            brew="neovim",
        ),
    ),
    ToolSpec(
        "psql",
        "PostgreSQL Client",
        BootstrapCategory.DATABASES,
        "psql",
        website="https://www.postgresql.org/",
        packages=_packages(
            apt="postgresql-client",
            dnf="postgresql",
            pacman="postgresql",
            zypper="postgresql",
            brew="libpq",
        ),
    ),
    ToolSpec(
        "mysql",
        "MySQL Client",
        BootstrapCategory.DATABASES,
        "mysql",
        website="https://www.mysql.com/",
        packages=_packages(
            apt="default-mysql-client",
            dnf="mysql",
            pacman="mysql",
            zypper="mysql-client",
            brew="mysql-client",
        ),
    ),
    ToolSpec(
        "sqlite3",
        "SQLite",
        BootstrapCategory.DATABASES,
        "sqlite3",
        website="https://sqlite.org/",
        packages=_packages(
            apt="sqlite3",
            dnf="sqlite",
            pacman="sqlite",
            zypper="sqlite3",
            xbps="sqlite",
            apk="sqlite",
            brew="sqlite",
        ),
    ),
    ToolSpec(
        "redis-cli",
        "Redis CLI",
        BootstrapCategory.DATABASES,
        "redis-cli",
        website="https://redis.io/",
        packages=_packages(
            apt="redis-tools", dnf="redis", pacman="redis", zypper="redis", brew="redis"
        ),
    ),
    ToolSpec(
        "ssh",
        "OpenSSH",
        BootstrapCategory.SSH,
        "ssh",
        website="https://www.openssh.com/",
        config_paths=("~/.ssh/config",),
        packages=_packages(
            apt="openssh-client",
            dnf="openssh-clients",
            pacman="openssh",
            zypper="openssh",
            xbps="openssh",
            apk="openssh",
            brew="openssh",
        ),
    ),
    ToolSpec(
        "gpg",
        "GnuPG",
        BootstrapCategory.GPG,
        "gpg",
        website="https://gnupg.org/",
        config_paths=("~/.gnupg/gpg.conf",),
        packages=_packages(
            apt="gnupg",
            dnf="gnupg2",
            pacman="gnupg",
            zypper="gpg2",
            xbps="gnupg2",
            apk="gnupg",
            brew="gnupg",
        ),
    ),
    ToolSpec(
        "ufw",
        "UFW",
        BootstrapCategory.SECURITY,
        "ufw",
        website="https://wiki.ubuntu.com/UncomplicatedFirewall",
        packages=_packages(apt="ufw", pacman="ufw", zypper="ufw"),
    ),
    ToolSpec(
        "nmap",
        "Nmap",
        BootstrapCategory.SECURITY,
        "nmap",
        website="https://nmap.org/",
        packages=_packages(
            apt="nmap",
            dnf="nmap",
            pacman="nmap",
            zypper="nmap",
            xbps="nmap",
            apk="nmap",
            brew="nmap",
        ),
    ),
    ToolSpec(
        "htop",
        "htop",
        BootstrapCategory.MONITORING,
        "htop",
        website="https://htop.dev/",
        packages=_packages(
            apt="htop",
            dnf="htop",
            pacman="htop",
            zypper="htop",
            xbps="htop",
            apk="htop",
            brew="htop",
        ),
    ),
    ToolSpec(
        "glances",
        "Glances",
        BootstrapCategory.MONITORING,
        "glances",
        website="https://nicolargo.github.io/glances/",
        packages=_packages(
            apt="glances", dnf="glances", pacman="glances", brew="glances", pipx="glances"
        ),
    ),
    ToolSpec(
        "jq",
        "jq",
        BootstrapCategory.TERMINAL_UTILITIES,
        "jq",
        website="https://jqlang.github.io/jq/",
        packages=_packages(
            apt="jq", dnf="jq", pacman="jq", zypper="jq", xbps="jq", apk="jq", brew="jq"
        ),
    ),
    ToolSpec(
        "ripgrep",
        "ripgrep",
        BootstrapCategory.TERMINAL_UTILITIES,
        "rg",
        website="https://github.com/BurntSushi/ripgrep",
        packages=_packages(
            apt="ripgrep",
            dnf="ripgrep",
            pacman="ripgrep",
            zypper="ripgrep",
            xbps="ripgrep",
            apk="ripgrep",
            brew="ripgrep",
        ),
    ),
    ToolSpec(
        "fd",
        "fd",
        BootstrapCategory.TERMINAL_UTILITIES,
        "fd",
        website="https://github.com/sharkdp/fd",
        packages=_packages(apt="fd-find", dnf="fd-find", pacman="fd", zypper="fd", brew="fd"),
    ),
    ToolSpec(
        "ruff",
        "Ruff",
        BootstrapCategory.PACKAGE_REGISTRIES,
        "ruff",
        website="https://docs.astral.sh/ruff/",
        packages=_packages(
            apt="ruff", dnf="ruff", pacman="ruff", brew="ruff", pipx="ruff", pip="ruff"
        ),
    ),
    ToolSpec(
        "fzf",
        "fzf",
        BootstrapCategory.SHELL_ENHANCEMENTS,
        "fzf",
        website="https://github.com/junegunn/fzf",
        packages=_packages(apt="fzf", dnf="fzf", pacman="fzf", zypper="fzf", brew="fzf"),
    ),
    ToolSpec(
        "starship",
        "Starship",
        BootstrapCategory.SHELL_ENHANCEMENTS,
        "starship",
        website="https://starship.rs/",
        config_paths=("~/.config/starship.toml",),
        packages=_packages(
            apt="starship", dnf="starship", pacman="starship", brew="starship", cargo="starship"
        ),
    ),
    ToolSpec(
        "mise",
        "mise",
        BootstrapCategory.VERSION_MANAGERS,
        "mise",
        website="https://mise.jdx.dev/",
        config_paths=("~/.config/mise/config.toml", "~/.tool-versions"),
        packages=_packages(brew="mise", cargo="mise"),
    ),
    ToolSpec(
        "asdf",
        "asdf",
        BootstrapCategory.VERSION_MANAGERS,
        "asdf",
        website="https://asdf-vm.com/",
        config_paths=("~/.asdfrc", "~/.tool-versions"),
        packages=_packages(apt="asdf", dnf="asdf", pacman="asdf-vm", brew="asdf"),
    ),
    ToolSpec(
        "flutter",
        "Flutter",
        BootstrapCategory.MOBILE_DEVELOPMENT,
        "flutter",
        website="https://flutter.dev/",
        packages=_packages(snap="flutter", brew="flutter", asdf="flutter latest"),
    ),
    ToolSpec(
        "adb",
        "Android Debug Bridge",
        BootstrapCategory.MOBILE_DEVELOPMENT,
        "adb",
        website="https://developer.android.com/tools/adb",
        packages=_packages(
            apt="adb",
            dnf="android-tools",
            pacman="android-tools",
            zypper="android-tools",
            brew="android-platform-tools",
        ),
    ),
    ToolSpec(
        "ollama",
        "Ollama",
        BootstrapCategory.AI,
        "ollama",
        website="https://ollama.com/",
        config_paths=("~/.ollama",),
        packages=_packages(brew="ollama"),
    ),
    ToolSpec(
        "nvcc",
        "CUDA Compiler",
        BootstrapCategory.AI,
        "nvcc",
        website="https://developer.nvidia.com/cuda-toolkit",
        packages=_packages(apt="nvidia-cuda-toolkit", dnf="cuda-toolkit", pacman="cuda"),
    ),
    ToolSpec(
        "gdb",
        "GDB",
        BootstrapCategory.DEBUGGERS,
        "gdb",
        website="https://sourceware.org/gdb/",
        packages=_packages(
            apt="gdb", dnf="gdb", pacman="gdb", zypper="gdb", xbps="gdb", apk="gdb", brew="gdb"
        ),
    ),
    ToolSpec(
        "strace",
        "strace",
        BootstrapCategory.DEBUGGERS,
        "strace",
        website="https://strace.io/",
        packages=_packages(
            apt="strace",
            dnf="strace",
            pacman="strace",
            zypper="strace",
            xbps="strace",
            apk="strace",
        ),
    ),
    ToolSpec(
        "radare2",
        "radare2",
        BootstrapCategory.REVERSE_ENGINEERING,
        "r2",
        website="https://rada.re/n/",
        packages=_packages(
            apt="radare2", dnf="radare2", pacman="radare2", zypper="radare2", brew="radare2"
        ),
    ),
    ToolSpec(
        "godot",
        "Godot",
        BootstrapCategory.GAME_DEVELOPMENT,
        "godot",
        website="https://godotengine.org/",
        packages=_packages(
            apt="godot3", dnf="godot", pacman="godot", flatpak="org.godotengine.Godot", brew="godot"
        ),
    ),
    ToolSpec(
        "systemctl",
        "systemd",
        BootstrapCategory.SYSTEM_SERVICES,
        "systemctl",
        website="https://systemd.io/",
        packages=_packages(apt="systemd", dnf="systemd", pacman="systemd", zypper="systemd"),
    ),
)


BOOTSTRAP_PROFILES: tuple[BootstrapProfile, ...] = (
    BootstrapProfile(
        "general",
        "General Developer",
        "Core workstation tools for most projects.",
        ("git", "curl", "wget", "python", "pip", "node", "npm", "docker", "vim", "jq", "ripgrep"),
    ),
    BootstrapProfile(
        "frontend",
        "Frontend",
        "JavaScript and browser-oriented development.",
        ("git", "node", "npm", "pnpm", "yarn", "bun", "code", "ripgrep", "fzf"),
    ),
    BootstrapProfile(
        "backend",
        "Backend",
        "API and service development with common databases.",
        ("git", "python", "pipx", "node", "go", "java", "docker", "psql", "mysql", "redis-cli"),
    ),
    BootstrapProfile(
        "python",
        "Python",
        "Python application and automation development.",
        ("git", "python", "pip", "pipx", "sqlite3", "ruff", "jq"),
    ),
    BootstrapProfile(
        "node",
        "Node",
        "Node.js service and frontend tooling.",
        ("git", "node", "npm", "pnpm", "yarn", "bun"),
    ),
    BootstrapProfile(
        "rust",
        "Rust",
        "Rust compiler, Cargo, and native build tools.",
        ("git", "rustc", "cargo", "gcc", "gdb", "cmake"),
    ),
    BootstrapProfile(
        "go",
        "Go",
        "Go toolchain and common backend utilities.",
        ("git", "go", "docker", "psql", "jq"),
    ),
    BootstrapProfile(
        "java", "Java", "Java runtime and build ecosystem.", ("git", "java", "docker", "psql")
    ),
    BootstrapProfile(
        "flutter",
        "Flutter",
        "Flutter and Android command-line development.",
        ("git", "flutter", "adb", "java", "code"),
    ),
    BootstrapProfile(
        "android",
        "Android",
        "Android platform tools and Java runtime.",
        ("git", "adb", "java", "code"),
    ),
    BootstrapProfile(
        "data-science",
        "Data Science",
        "Python, notebooks, and database clients.",
        ("git", "python", "pip", "pipx", "sqlite3", "psql"),
    ),
    BootstrapProfile(
        "ai",
        "AI Engineer",
        "Local AI and GPU-oriented tooling.",
        ("git", "python", "pipx", "ollama", "nvcc", "docker"),
    ),
    BootstrapProfile(
        "security",
        "Cyber Security",
        "Safe local security and reverse-engineering tools.",
        ("git", "nmap", "gpg", "ssh", "strace", "gdb", "radare2"),
    ),
    BootstrapProfile(
        "devops",
        "DevOps",
        "Container, Kubernetes, IaC, and cloud CLI tooling.",
        (
            "git",
            "docker",
            "podman",
            "kubectl",
            "helm",
            "terraform",
            "ansible",
            "gh",
            "aws",
            "az",
            "gcloud",
        ),
    ),
    BootstrapProfile(
        "cloud",
        "Cloud Engineer",
        "Cloud CLIs and infrastructure tooling.",
        ("git", "gh", "aws", "az", "gcloud", "terraform", "kubectl"),
    ),
    BootstrapProfile(
        "game",
        "Game Developer",
        "Native build tools and Godot.",
        ("git", "gcc", "clang", "cmake", "ninja", "godot"),
    ),
)
