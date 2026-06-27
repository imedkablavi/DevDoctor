from __future__ import annotations

import platform
from pathlib import Path

import pytest

from devdoctor.checks.cpu import _cpu_model


def test_cpu_model_reads_proc_cpuinfo_when_platform_is_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cpuinfo = tmp_path / "cpuinfo"
    cpuinfo.write_text(
        "processor\t: 0\nmodel name\t: Example CPU 9000\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(platform, "processor", lambda: "")

    assert _cpu_model(cpuinfo) == "Example CPU 9000"
