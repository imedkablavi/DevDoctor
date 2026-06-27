"""Operating system and distribution detection."""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

import psutil

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import get_hostname, get_username, read_os_release


def check_os() -> CheckResult:
    """Detect the Linux distribution and whether it is officially supported."""

    release = read_os_release()
    distro_id = release.get("ID", "").lower()
    id_like = {item.lower() for item in release.get("ID_LIKE", "").split()}
    supported_ids = {"ubuntu", "debian", "fedora", "bazzite", "arch", "manjaro", "pop", "linuxmint"}
    supported = distro_id in supported_ids or bool(id_like.intersection(supported_ids))
    pretty_name = release.get("PRETTY_NAME") or platform.platform()
    details = {
        "hostname": get_hostname(),
        "username": get_username(),
        "distribution": pretty_name,
        "distribution_id": distro_id or "unknown",
        "distribution_like": sorted(id_like),
        "distribution_version": release.get("VERSION_ID", "unknown"),
        "supported_distribution": supported,
        "desktop_environment": _first_env(
            "XDG_CURRENT_DESKTOP",
            "XDG_SESSION_DESKTOP",
            "DESKTOP_SESSION",
        ),
        "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown") or "unknown",
        "shell": _shell_name(),
        "terminal": _first_env("TERM_PROGRAM", "TERMINAL", "TERM"),
        "primary_package_manager": _primary_package_manager(distro_id),
        "battery": _battery_label(),
        "temperature": _temperature_label(),
    }

    if supported:
        return CheckResult.ok(
            id="system.os",
            title="Linux Distribution",
            category=CheckCategory.SYSTEM,
            summary=f"{pretty_name} is supported.",
            details=details,
            weight=2,
        )

    return CheckResult.warning(
        id="system.os",
        title="Linux Distribution",
        category=CheckCategory.SYSTEM,
        summary=f"{pretty_name} is not in the supported distribution list.",
        details=details,
        recommendation="DevDoctor will continue, but package-manager guidance may be less precise.",
        weight=1,
    )


def _first_env(*names: str) -> str:
    """Return the first non-empty environment value from a list."""

    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return "unknown"


def _shell_name() -> str:
    """Return a readable shell name from the environment."""

    shell = os.environ.get("SHELL")
    if not shell:
        return "unknown"
    return Path(shell).name or shell


def _primary_package_manager(distro_id: str = "") -> str:
    """Return the first native package manager detected on PATH."""

    candidates = (
        ("apt", "APT"),
        ("dnf", "DNF"),
        ("rpm-ostree", "rpm-ostree"),
        ("pacman", "Pacman"),
        ("rpm", "RPM"),
        ("brew", "Homebrew"),
    )
    if distro_id == "bazzite":
        candidates = (
            ("brew", "Homebrew"),
            ("rpm-ostree", "rpm-ostree"),
            ("dnf", "DNF"),
            ("rpm", "RPM"),
        )

    for executable, title in candidates:
        if shutil.which(executable):
            return title
    return "unknown"


def _battery_label() -> str:
    """Return battery state when psutil can read it."""

    battery = psutil.sensors_battery()
    if battery is None:
        return "Not detected"
    plugged = "charging" if battery.power_plugged else "discharging"
    return f"{battery.percent:.0f}% ({plugged})"


def _temperature_label() -> str:
    """Return the highest available sensor temperature."""

    if not hasattr(psutil, "sensors_temperatures"):
        return "Not detected"
    try:
        temperatures = psutil.sensors_temperatures(fahrenheit=False)
    except (OSError, RuntimeError):
        return "Not detected"
    readings = [
        entry.current
        for entries in temperatures.values()
        for entry in entries
        if entry.current is not None
    ]
    if not readings:
        return "Not detected"
    return f"{max(readings):.1f} C"
