"""Minimal dependency-free PDF report exporter."""

from __future__ import annotations

import textwrap
from pathlib import Path

from devdoctor.models import HealthReport


def render_pdf(report: HealthReport) -> bytes:
    """Render a compact single-font PDF health report."""

    lines = _report_lines(report)
    content = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
    for index, line in enumerate(lines):
        if index:
            content.append("T*")
        content.append(f"({_escape_pdf_text(line)}) Tj")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    return _build_pdf(objects)


def write_pdf_report(report: HealthReport, path: Path) -> Path:
    """Write a compact PDF report to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_pdf(report))
    return path


def _report_lines(report: HealthReport) -> list[str]:
    summary = report.summary
    lines = [
        "DevDoctor Health Report",
        f"Generated: {report.generated_at.isoformat()}",
        f"Score: {report.score}/100",
        f"Passed: {summary.passed}  Warnings: {summary.warnings}  Failed: {summary.failed}",
        "",
        "Recommendations:",
    ]
    recommendations = report.recommendations or (
        "No recommendations. Your development environment looks healthy.",
    )
    for recommendation in recommendations:
        lines.extend(textwrap.wrap(f"- {recommendation}", width=88))
    lines.extend(["", "Checks:"])
    for result in report.results:
        check_line = f"[{result.status.value.upper()}] {result.title}: {result.summary}"
        lines.extend(textwrap.wrap(check_line, width=88))
        if len(lines) > 52:
            lines.append(
                "Report truncated for compact PDF export. "
                "Use JSON, HTML, or Markdown for full data."
            )
            break
    return lines


def _build_pdf(objects: list[bytes]) -> bytes:
    chunks = [b"%PDF-1.4\n"]
    offsets: list[int] = []
    for index, payload in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n".encode("ascii"))
        chunks.append(payload)
        chunks.append(b"\nendobj\n")

    xref_offset = sum(len(chunk) for chunk in chunks)
    chunks.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    chunks.append(b"0000000000 65535 f \n")
    for offset in offsets:
        chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    chunks.append(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    return b"".join(chunks)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
