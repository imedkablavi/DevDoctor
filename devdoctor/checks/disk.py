"""Disk space checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import psutil

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import format_bytes


@dataclass(frozen=True, slots=True)
class PartitionInfo:
    """Filesystem information for the partition that owns a path."""

    device: str
    fstype: str
    mountpoint: str


def check_disk() -> CheckResult:
    """Check disk usage for the user's home filesystem."""

    path = Path.home()
    usage = psutil.disk_usage(str(path))
    partition = _partition_for_path(path)
    details = {
        "disk_path": str(path),
        "disk_total": format_bytes(usage.total),
        "disk_used": format_bytes(usage.used),
        "disk_free": format_bytes(usage.free),
        "disk_used_percent": round(usage.percent, 1),
        "disk_free_bytes": usage.free,
        "filesystem": partition.fstype if partition else "unknown",
        "disk_device": partition.device if partition else "unknown",
        "disk_mountpoint": partition.mountpoint if partition else str(path),
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


def _partition_for_path(path: Path) -> PartitionInfo | None:
    """Return the mounted partition that owns a path."""

    try:
        resolved = path.resolve()
        partitions = psutil.disk_partitions(all=True)
    except OSError:
        return None

    best_match: PartitionInfo | None = None
    best_length = -1
    for partition in partitions:
        mountpoint = Path(partition.mountpoint)
        try:
            resolved.relative_to(mountpoint)
        except ValueError:
            continue
        length = len(str(mountpoint))
        if length > best_length:
            best_match = PartitionInfo(
                device=partition.device,
                fstype=partition.fstype,
                mountpoint=partition.mountpoint,
            )
            best_length = length
    return best_match
