"""Kernel and architecture checks."""

from __future__ import annotations

import platform

from devdoctor.models import CheckCategory, CheckResult


def check_kernel() -> CheckResult:
    """Collect kernel and machine architecture information."""

    release = platform.release()
    details = {
        "kernel": release,
        "kernel_version": platform.version(),
        "architecture": platform.machine() or "unknown",
        "python_platform": platform.platform(),
    }
    return CheckResult.ok(
        id="system.kernel",
        title="Kernel",
        category=CheckCategory.SYSTEM,
        summary=f"Linux kernel {release} on {details['architecture']}.",
        details=details,
        weight=1,
    )
