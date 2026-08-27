"""Package manager detection, host policy, and safe install planning."""

from __future__ import annotations

import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from devdoctor.utils import parse_version, read_os_release, run_command


@dataclass(frozen=True, slots=True)
class PackageManagerInfo:
    """Detected package-manager availability."""

    id: str
    title: str
    executable: str
    installed: bool
    path: str | None
    family: str
    version: str | None
    command_hint: str


@dataclass(frozen=True, slots=True)
class PackageManagerConflict:
    """A package-manager combination that deserves explicit user review."""

    kind: str
    managers: tuple[str, ...]
    severity: str
    message: str


@dataclass(frozen=True, slots=True)
class InstallPlan:
    """A distro-aware install plan for a missing developer tool."""

    tool_id: str
    tool_title: str
    command: str
    manager: str
    note: str
    requires_confirmation: bool = True


PACKAGE_MANAGERS: tuple[tuple[str, str, str, str, str], ...] = (
    ("apt", "APT", "apt", "system", "sudo apt install <package>"),
    ("dnf", "DNF", "dnf", "system", "sudo dnf install <package>"),
    ("rpm-ostree", "rpm-ostree", "rpm-ostree", "system", "rpm-ostree install <package>"),
    ("pacman", "Pacman", "pacman", "system", "sudo pacman -S <package>"),
    ("yay", "yay", "yay", "system", "yay -S <package>"),
    ("paru", "paru", "paru", "system", "paru -S <package>"),
    ("zypper", "Zypper", "zypper", "system", "sudo zypper install <package>"),
    ("xbps", "XBPS", "xbps-install", "system", "sudo xbps-install <package>"),
    ("apk", "APK", "apk", "system", "sudo apk add <package>"),
    ("rpm", "RPM", "rpm", "system-query", "rpm -qa"),
    ("nix", "Nix", "nix", "user", "nix profile install <package>"),
    ("flatpak", "Flatpak", "flatpak", "desktop", "flatpak install <remote> <app>"),
    ("snap", "Snap", "snap", "desktop", "sudo snap install <package>"),
    ("brew", "Homebrew", "brew", "user", "brew install <formula>"),
    ("cargo", "Cargo", "cargo", "language", "cargo install <crate>"),
    ("go", "Go", "go", "language", "go install <module>"),
    ("pip", "pip", "pip", "language", "python -m pip install <package>"),
    ("pipx", "pipx", "pipx", "language", "pipx install <package>"),
    ("npm", "npm", "npm", "language", "npm install <package>"),
    ("pnpm", "pnpm", "pnpm", "language", "pnpm add <package>"),
    ("yarn", "Yarn", "yarn", "language", "yarn global add <package>"),
    ("bun", "Bun", "bun", "language", "bun add <package>"),
    ("gem", "RubyGems", "gem", "language", "gem install <package>"),
    ("composer", "Composer", "composer", "language", "composer global require <package>"),
    ("rustup", "Rustup", "rustup", "language", "rustup toolchain install <toolchain>"),
    ("flutter", "Flutter", "flutter", "language", "flutter pub global activate <package>"),
    ("mise", "mise", "mise", "version-manager", "mise use -g <runtime>"),
    ("asdf", "asdf", "asdf", "version-manager", "asdf install <plugin> <version>"),
)

APT_PACKAGES = {
    "tool.git": "git",
    "tool.python": "python3 python3-pip",
    "tool.docker": "docker.io",
    "tool.podman": "podman",
    "tool.node": "nodejs npm",
    "tool.npm": "npm",
    "tool.pnpm": "pnpm",
    "tool.bun": "bun",
    "tool.rust": "rustc cargo",
    "tool.cargo": "cargo",
    "tool.go": "golang-go",
    "tool.java": "default-jdk",
    "tool.github_cli": "gh",
    "tool.kubectl": "kubectl",
    "tool.helm": "helm",
    "tool.terraform": "terraform",
}

DNF_PACKAGES = {
    "tool.git": "git",
    "tool.python": "python3 python3-pip",
    "tool.docker": "moby-engine docker-compose",
    "tool.podman": "podman",
    "tool.node": "nodejs npm",
    "tool.npm": "npm",
    "tool.pnpm": "pnpm",
    "tool.bun": "bun",
    "tool.rust": "rust cargo",
    "tool.cargo": "cargo",
    "tool.go": "golang",
    "tool.java": "java-latest-openjdk-devel",
    "tool.github_cli": "gh",
    "tool.kubectl": "kubernetes-client",
    "tool.helm": "helm",
    "tool.terraform": "terraform",
}

PACMAN_PACKAGES = {
    "tool.git": "git",
    "tool.python": "python python-pip",
    "tool.docker": "docker",
    "tool.podman": "podman",
    "tool.node": "nodejs npm",
    "tool.npm": "npm",
    "tool.pnpm": "pnpm",
    "tool.bun": "bun",
    "tool.rust": "rust",
    "tool.cargo": "cargo",
    "tool.go": "go",
    "tool.java": "jdk-openjdk",
    "tool.github_cli": "github-cli",
    "tool.kubectl": "kubectl",
    "tool.helm": "helm",
    "tool.terraform": "terraform",
}

ZYPPER_PACKAGES = {
    "tool.git": "git",
    "tool.python": "python3 python3-pip",
    "tool.docker": "docker",
    "tool.podman": "podman",
    "tool.node": "nodejs npm",
    "tool.npm": "npm",
    "tool.rust": "rust cargo",
    "tool.cargo": "cargo",
    "tool.go": "go",
    "tool.java": "java-openjdk-devel",
    "tool.github_cli": "gh",
    "tool.kubectl": "kubectl",
    "tool.helm": "helm",
    "tool.terraform": "terraform",
}

BREW_PACKAGES = {
    "tool.git": "git",
    "tool.python": "python",
    "tool.docker": "docker",
    "tool.podman": "podman",
    "tool.node": "node",
    "tool.npm": "node",
    "tool.pnpm": "pnpm",
    "tool.bun": "bun",
    "tool.rust": "rustup-init",
    "tool.cargo": "rustup-init",
    "tool.go": "go",
    "tool.java": "openjdk",
    "tool.github_cli": "gh",
    "tool.kubectl": "kubectl",
    "tool.helm": "helm",
    "tool.terraform": "terraform",
}

NIX_PACKAGES = {
    "tool.git": "nixpkgs#git",
    "tool.python": "nixpkgs#python3",
    "tool.podman": "nixpkgs#podman",
    "tool.node": "nixpkgs#nodejs",
    "tool.npm": "nixpkgs#nodejs",
    "tool.pnpm": "nixpkgs#pnpm",
    "tool.bun": "nixpkgs#bun",
    "tool.rust": "nixpkgs#rustup",
    "tool.cargo": "nixpkgs#rustup",
    "tool.go": "nixpkgs#go",
    "tool.java": "nixpkgs#jdk",
    "tool.github_cli": "nixpkgs#gh",
    "tool.kubectl": "nixpkgs#kubectl",
    "tool.helm": "nixpkgs#kubernetes-helm",
    "tool.terraform": "nixpkgs#terraform",
}

ATOMIC_VARIANTS = {
    "atomic",
    "silverblue",
    "kinoite",
    "sericea",
    "sway-atomic",
    "onyx",
    "budgie-atomic",
    "bazzite",
    "bluefin",
    "aurora",
}

SYSTEM_MUTATION_MANAGERS = {"apt", "dnf", "rpm-ostree", "pacman", "zypper", "xbps", "apk"}


def detect_package_managers() -> tuple[PackageManagerInfo, ...]:
    """Detect common Linux package managers and language package managers."""

    managers: list[PackageManagerInfo] = []
    for manager_id, title, executable, family, command_hint in PACKAGE_MANAGERS:
        path = shutil.which(executable)
        managers.append(
            PackageManagerInfo(
                id=manager_id,
                title=title,
                executable=executable,
                installed=path is not None,
                path=path,
                family=family,
                version=_manager_version(path),
                command_hint=command_hint,
            )
        )
    return tuple(managers)


def _manager_version(path: str | None) -> str | None:
    """Return a package-manager version without failing detection."""

    if path is None:
        return None
    result = run_command((path, "--version"), timeout=3)
    return parse_version(result.combined_output)


def is_atomic_host(
    release: Mapping[str, str] | None = None,
    managers: Iterable[PackageManagerInfo] | None = None,
) -> bool:
    """Return whether host package mutation should be treated as image-based."""

    release_data = dict(release or read_os_release())
    distro_id = release_data.get("ID", "").lower()
    variant_id = release_data.get("VARIANT_ID", "").lower()
    image_id = release_data.get("IMAGE_ID", "").lower()
    if distro_id == "bazzite" or variant_id in ATOMIC_VARIANTS or image_id in ATOMIC_VARIANTS:
        return True
    if release_data.get("OSTREE_VERSION"):
        return True
    installed = {
        manager.id for manager in (managers or detect_package_managers()) if manager.installed
    }
    return (
        distro_id in {"fedora", "ublue", "universal-blue"}
        and "rpm-ostree" in installed
        and (variant_id in ATOMIC_VARIANTS or bool(release_data.get("OSTREE_VERSION")))
    )


def package_manager_conflicts(
    managers: Iterable[PackageManagerInfo],
    release: Mapping[str, str] | None = None,
) -> tuple[PackageManagerConflict, ...]:
    """Identify mixed-manager states that can cause unsafe or misleading repair plans."""

    manager_tuple = tuple(managers)
    installed = {manager.id for manager in manager_tuple if manager.installed}
    conflicts: list[PackageManagerConflict] = []

    if is_atomic_host(release, manager_tuple) and "dnf" in installed:
        conflicts.append(
            PackageManagerConflict(
                kind="atomic-host-dnf",
                managers=("rpm-ostree", "dnf"),
                severity="high",
                message=(
                    "Image-based Fedora/Bazzite host detected. DNF may be present for queries or "
                    "containers, but DevDoctor must not recommend it for host mutations."
                ),
            )
        )

    system_managers = tuple(sorted(installed.intersection(SYSTEM_MUTATION_MANAGERS)))
    native_without_query_helpers = tuple(
        manager for manager in system_managers if manager != "rpm-ostree"
    )
    if len(native_without_query_helpers) > 1:
        conflicts.append(
            PackageManagerConflict(
                kind="multiple-system-managers",
                managers=native_without_query_helpers,
                severity="medium",
                message=(
                    "Multiple system package managers are on PATH. DevDoctor will use distro "
                    "policy instead of whichever executable happens to appear first."
                ),
            )
        )

    if {"npm", "pnpm", "yarn"}.issubset(installed):
        conflicts.append(
            PackageManagerConflict(
                kind="node-global-manager-overlap",
                managers=("npm", "pnpm", "yarn"),
                severity="low",
                message=(
                    "Multiple Node global package managers are installed; duplicate global tools "
                    "and PATH shadowing are possible."
                ),
            )
        )

    return tuple(conflicts)


def install_plan_for_tool(tool_id: str, tool_title: str) -> InstallPlan | None:
    """Return a distro-aware install plan for a known missing tool."""

    release = read_os_release()
    distro_id = release.get("ID", "").lower()
    distro_like = {item.lower() for item in release.get("ID_LIKE", "").split()}
    managers = detect_package_managers()
    installed = {manager.id for manager in managers if manager.installed}

    if is_atomic_host(release, managers):
        package = BREW_PACKAGES.get(tool_id)
        if "brew" in installed and package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"brew install {package}",
                manager="Homebrew",
                note=(
                    "Image-based host detected; Homebrew keeps developer tools in user space "
                    "without layering the base image."
                ),
            )
        package = DNF_PACKAGES.get(tool_id)
        if "rpm-ostree" in installed and package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"rpm-ostree install {package}",
                manager="rpm-ostree",
                note=(
                    "Image-based host detected. This creates a layered deployment and may require "
                    "a reboot; DevDoctor never substitutes dnf for host mutation."
                ),
            )
        return None

    if distro_id in {"ubuntu", "debian", "linuxmint", "pop"} or distro_like.intersection(
        {"ubuntu", "debian"}
    ):
        package = APT_PACKAGES.get(tool_id)
        if package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"sudo apt install {package}",
                manager="APT",
                note="Review third-party repository requirements for vendor-managed tools.",
            )

    if distro_id == "fedora" or "fedora" in distro_like:
        package = DNF_PACKAGES.get(tool_id)
        if package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"sudo dnf install {package}",
                manager="DNF",
                note="DNF is the native package manager for mutable Fedora systems.",
            )

    if distro_id in {"arch", "manjaro"} or "arch" in distro_like:
        package = PACMAN_PACKAGES.get(tool_id)
        if package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"sudo pacman -S {package}",
                manager="Pacman",
                note="Pacman installs packages from configured Arch-compatible repositories.",
            )

    if (
        distro_id in {"opensuse", "opensuse-tumbleweed", "opensuse-leap", "sles"}
        or "suse" in distro_like
    ):
        package = ZYPPER_PACKAGES.get(tool_id)
        if package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"sudo zypper install {package}",
                manager="Zypper",
                note="Zypper is the native package manager for SUSE-family systems.",
            )

    package = BREW_PACKAGES.get(tool_id)
    if "brew" in installed and package:
        return InstallPlan(
            tool_id=tool_id,
            tool_title=tool_title,
            command=f"brew install {package}",
            manager="Homebrew",
            note="Homebrew is available and can install this developer tool without sudo.",
        )

    package = NIX_PACKAGES.get(tool_id)
    if "nix" in installed and package:
        return InstallPlan(
            tool_id=tool_id,
            tool_title=tool_title,
            command=f"nix profile install {package}",
            manager="Nix",
            note="Nix is available; this plan installs into the current user profile.",
        )
    return None
