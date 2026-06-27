"""GPU detection for common Linux workstations."""

from __future__ import annotations

import shutil

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.utils import run_command


def check_gpu() -> CheckResult:
    """Detect GPUs through lspci or nvidia-smi when available."""

    lspci = shutil.which("lspci")
    if lspci:
        result = run_command((lspci,), timeout=3)
        gpus = [
            line.strip()
            for line in result.stdout.splitlines()
            if any(
                label in line.lower() for label in ("vga compatible", "3d controller", "display")
            )
        ]
        if gpus:
            return CheckResult.ok(
                id="system.gpu",
                title="GPU",
                category=CheckCategory.SYSTEM,
                summary=f"{len(gpus)} GPU device(s) detected.",
                details={"gpu": gpus[0], "gpus": gpus},
                weight=0,
            )

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        result = run_command(
            (
                nvidia_smi,
                "--query-gpu=name,driver_version",
                "--format=csv,noheader",
            ),
            timeout=4,
        )
        gpus = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if gpus:
            return CheckResult.ok(
                id="system.gpu",
                title="GPU",
                category=CheckCategory.SYSTEM,
                summary=f"{len(gpus)} NVIDIA GPU device(s) detected.",
                details={"gpu": gpus[0], "gpus": gpus},
                weight=0,
            )

    return CheckResult.warning(
        id="system.gpu",
        title="GPU",
        category=CheckCategory.SYSTEM,
        summary="GPU information could not be detected with lspci or nvidia-smi.",
        details={
            "gpu": None,
            "detection_tools": {"lspci": bool(lspci), "nvidia_smi": bool(nvidia_smi)},
        },
        recommendation="Install pciutils for lspci-based GPU detection if GPU inventory matters.",
        weight=0,
    )
