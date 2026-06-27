"""JSON report exporter."""

from __future__ import annotations

import json
from pathlib import Path

from devdoctor.models import HealthReport


def render_json(report: HealthReport, *, pretty: bool = True) -> str:
    """Render a health report as JSON."""

    return json.dumps(
        report.to_dict(),
        indent=2 if pretty else None,
        sort_keys=False,
        ensure_ascii=False,
    )


def write_json_report(report: HealthReport, path: Path, *, pretty: bool = True) -> Path:
    """Write a health report to a JSON file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_json(report, pretty=pretty) + "\n", encoding="utf-8")
    return path
