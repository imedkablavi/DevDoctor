"""Operating system and distribution detection."""

from __future__ import annotations

import platform

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
