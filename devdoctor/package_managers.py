"""Package manager detection and install command planning."""

from __future__ import annotations

import shutil
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
    ("rpm", "RPM", "rpm", "system", "rpm -qa"),
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


def install_plan_for_tool(tool_id: str, tool_title: str) -> InstallPlan | None:
    """Return a distro-aware install plan for a known missing tool."""

    release = read_os_release()
    distro_id = release.get("ID", "").lower()
    distro_like = {item.lower() for item in release.get("ID_LIKE", "").split()}

    if distro_id == "bazzite":
        package = BREW_PACKAGES.get(tool_id)
        if shutil.which("brew") and package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"brew install {package}",
                manager="Homebrew",
                note=(
                    "Bazzite is image-based; Homebrew keeps developer tools in user space "
                    "without layering system packages."
                ),
            )
        package = DNF_PACKAGES.get(tool_id)
        if package:
            return InstallPlan(
                tool_id=tool_id,
                tool_title=tool_title,
                command=f"rpm-ostree install {package}",
                manager="rpm-ostree",
                note=(
                    "Bazzite uses rpm-ostree for system layering. Reboot after layering "
                    "packages, or prefer Homebrew/distrobox for developer tools."
                ),
            )

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
                note="DNF is the native Fedora package manager.",
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

    package = BREW_PACKAGES.get(tool_id)
    if shutil.which("brew") and package:
        return InstallPlan(
            tool_id=tool_id,
            tool_title=tool_title,
            command=f"brew install {package}",
            manager="Homebrew",
            note="Homebrew is available and can install this developer tool without sudo.",
        )
    return None
