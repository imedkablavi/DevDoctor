"""CPU inventory checks."""

from __future__ import annotations

import platform
from pathlib import Path

import psutil

from devdoctor.models import CheckCategory, CheckResult


def check_cpu() -> CheckResult:
    """Collect CPU model, core count, and load information."""

    logical = psutil.cpu_count(logical=True) or 0
    physical = psutil.cpu_count(logical=False) or 0
    load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0.0, 0.0, 0.0)
    model = _cpu_model()
    details = {
        "cpu": model,
        "logical_cores": logical,
        "physical_cores": physical,
        "load_1m": round(load[0], 2),
        "load_5m": round(load[1], 2),
        "load_15m": round(load[2], 2),
    }
    if logical < 2:
        return CheckResult.warning(
            id="system.cpu",
            title="CPU",
            category=CheckCategory.SYSTEM,
            summary="Only one logical CPU core is visible.",
            details=details,
            recommendation="Developer workloads are more reliable with at least two CPU cores.",
            weight=2,
        )
    return CheckResult.ok(
        id="system.cpu",
        title="CPU",
        category=CheckCategory.SYSTEM,
        summary=f"{logical} logical CPU cores detected.",
        details=details,
        weight=1,
    )


def _cpu_model(cpuinfo_path: Path = Path("/proc/cpuinfo")) -> str:
    """Return a useful CPU model string from platform data or /proc/cpuinfo."""

    processor = platform.processor().strip()
    if processor:
        return processor

    try:
        for line in cpuinfo_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip().lower() in {"model name", "hardware"}:
                stripped = value.strip()
                if stripped:
                    return stripped
    except OSError:
        return "unknown CPU"
    return "unknown CPU"
