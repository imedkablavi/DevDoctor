"""Memory capacity checks."""

from __future__ import annotations

import psutil

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import format_bytes


def check_ram() -> CheckResult:
    """Collect RAM capacity and utilization."""

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    details = {
        "ram_total": format_bytes(memory.total),
        "ram_available": format_bytes(memory.available),
        "ram_used_percent": round(memory.percent, 1),
        "ram_total_bytes": memory.total,
        "ram_available_bytes": memory.available,
        "swap_total": format_bytes(swap.total),
        "swap_free": format_bytes(swap.free),
        "swap_used_percent": round(swap.percent, 1),
        "swap_total_bytes": swap.total,
        "swap_free_bytes": swap.free,
    }
    if memory.total < 4 * 1024**3:
        return CheckResult.warning(
            id="system.ram",
            title="RAM",
            category=CheckCategory.SYSTEM,
            summary=f"Low RAM capacity detected: {format_bytes(memory.total)}.",
            details=details,
            recommendation="Upgrade to at least 8 GiB RAM for modern development workloads.",
            weight=3,
        )
    if memory.percent >= 90:
        return CheckResult.warning(
            id="system.ram",
            title="RAM",
            category=CheckCategory.SYSTEM,
            summary=f"RAM usage is high at {memory.percent:.1f}%.",
            details=details,
            recommendation=(
                "Close memory-heavy applications before running large builds or containers."
            ),
            weight=2,
        )
    return CheckResult.ok(
        id="system.ram",
        title="RAM",
        category=CheckCategory.SYSTEM,
        summary=(
            f"{format_bytes(memory.total)} RAM with {format_bytes(memory.available)} available."
        ),
        details=details,
        weight=2,
    )
