from __future__ import annotations

import json
from datetime import UTC, datetime

from devdoctor.doctor import create_report
from devdoctor.exporters.html import render_html
from devdoctor.exporters.json import render_json
from devdoctor.exporters.markdown import render_markdown
from devdoctor.exporters.pdf import render_pdf
from devdoctor.models import CheckCategory, CheckResult


def test_create_report_counts_results_and_recommendations() -> None:
    report = create_report(
        results=(
            CheckResult.ok(
                id="system.os",
                title="OS",
                category=CheckCategory.SYSTEM,
                summary="supported",
                details={"distribution": "Fedora"},
            ),
            CheckResult.warning(
                id="tool.node",
                title="Node.js",
                category=CheckCategory.TOOL,
                summary="missing",
                recommendation="Install Node.js.",
            ),
        ),
        duration_seconds=1.25,
        generated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    assert report.summary.passed == 1
    assert report.summary.warnings == 1
    assert report.summary.failed == 0
    assert report.recommendations == ("Install Node.js.",)
    assert report.system_info["distribution"] == "Fedora"


def test_json_exporter_renders_valid_report_json() -> None:
    report = create_report(
        results=(
            CheckResult.ok(
                id="system.os",
                title="OS",
                category=CheckCategory.SYSTEM,
                summary="supported",
            ),
        ),
        duration_seconds=0.1,
        generated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    rendered = render_json(report)
    parsed = json.loads(rendered)

    assert parsed["score"] == 100
    assert parsed["summary"]["passed"] == 1
    assert parsed["results"][0]["id"] == "system.os"


def test_html_exporter_contains_score_and_result_summary() -> None:
    report = create_report(
        results=(
            CheckResult.failure(
                id="network.internet",
                title="Internet Connectivity",
                category=CheckCategory.NETWORK,
                summary="offline",
                recommendation="Check network.",
                weight=5,
            ),
        ),
        duration_seconds=0.1,
        generated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    rendered = render_html(report)

    assert "DevDoctor Health Report" in rendered
    assert "Internet Connectivity" in rendered
    assert "Check network." in rendered


def test_markdown_exporter_contains_report_table() -> None:
    report = create_report(
        results=(
            CheckResult.ok(
                id="tool.git",
                title="Git",
                category=CheckCategory.TOOL,
                summary="available",
            ),
        ),
        duration_seconds=0.1,
        generated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    rendered = render_markdown(report)

    assert "# DevDoctor Health Report" in rendered
    assert "| OK | Git | tool | available |  |" in rendered


def test_pdf_exporter_returns_pdf_bytes() -> None:
    report = create_report(
        results=(
            CheckResult.ok(
                id="tool.git",
                title="Git",
                category=CheckCategory.TOOL,
                summary="available",
            ),
        ),
        duration_seconds=0.1,
        generated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    rendered = render_pdf(report)

    assert rendered.startswith(b"%PDF-1.4")
    assert b"%%EOF" in rendered
