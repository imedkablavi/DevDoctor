"""System uptime check."""

from __future__ import annotations

import time

import psutil

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import format_duration


def check_uptime() -> CheckResult:
    """Collect system uptime."""

    boot_time = psutil.boot_time()
    uptime_seconds = max(0, int(time.time() - boot_time))
    return CheckResult.ok(
        id="system.uptime",
        title="Uptime",
        category=CheckCategory.SYSTEM,
        summary=f"System uptime is {format_duration(uptime_seconds)}.",
        details={
            "uptime": format_duration(uptime_seconds),
            "uptime_seconds": uptime_seconds,
            "boot_time_epoch": int(boot_time),
        },
        weight=0,
    )
