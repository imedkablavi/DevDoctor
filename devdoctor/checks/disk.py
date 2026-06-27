"""Disk space checks."""

from __future__ import annotations

from pathlib import Path

import psutil

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import format_bytes


def check_disk() -> CheckResult:
    """Check disk usage for the user's home filesystem."""

    path = Path.home()
    usage = psutil.disk_usage(str(path))
    details = {
        "disk_path": str(path),
        "disk_total": format_bytes(usage.total),
        "disk_used": format_bytes(usage.used),
        "disk_free": format_bytes(usage.free),
        "disk_used_percent": round(usage.percent, 1),
        "disk_free_bytes": usage.free,
    }
    if usage.free < 10 * 1024**3 or usage.percent >= 90:
        return CheckResult.warning(
            id="system.disk",
            title="Disk Space",
            category=CheckCategory.SYSTEM,
            summary=f"Disk space is tight: {format_bytes(usage.free)} free on {path}.",
            details=details,
            recommendation=(
                "Free at least 10 GiB before large builds, package installs, or container pulls."
            ),
            weight=3,
        )
    return CheckResult.ok(
        id="system.disk",
        title="Disk Space",
        category=CheckCategory.SYSTEM,
        summary=f"{format_bytes(usage.free)} free on {path}.",
        details=details,
        weight=2,
    )
