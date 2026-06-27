"""Rich tables and panels for DevDoctor reports."""

from __future__ import annotations

from collections.abc import Mapping

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from devdoctor.models import CheckCategory, CheckResult, HealthReport, JsonValue
from devdoctor.ui.theme import score_style, status_icon, status_style


def report_group(report: HealthReport) -> Group:
    """Create the full Rich report layout."""

    renderables: list[object] = [
        summary_panel(report),
        system_panel(report.system_info),
        results_table(report),
        recommendations_panel(report),
    ]
    return Group(*renderables)


def summary_panel(report: HealthReport) -> Panel:
    """Render score and status counts."""

    summary = report.summary
    grid = Table.grid(expand=True)
    grid.add_column(justify="center")
    grid.add_column(justify="center")
    grid.add_column(justify="center")
    grid.add_column(justify="center")
    grid.add_row(
        _metric("Health", f"{report.score}/100", score_style(report.score)),
        _metric("✓ Passed", str(summary.passed), "success"),
        _metric("⚠ Warnings", str(summary.warnings), "warning"),
        _metric("✕ Failed", str(summary.failed), "error"),
    )
    return Panel(
        grid,
        title="Health Overview",
        border_style=score_style(report.score),
        box=box.ROUNDED,
    )


def system_panel(system_info: Mapping[str, JsonValue]) -> Panel:
    """Render key system facts."""

    table = Table.grid(expand=True)
    table.add_column(style="muted", ratio=1)
    table.add_column(ratio=2)
    keys = (
        ("Hostname", "hostname"),
        ("Username", "username"),
        ("Distribution", "distribution"),
        ("Kernel", "kernel"),
        ("Architecture", "architecture"),
        ("CPU", "cpu"),
        ("Logical Cores", "logical_cores"),
        ("RAM", "ram_total"),
        ("Disk Free", "disk_free"),
        ("Uptime", "uptime"),
        ("GPU", "gpu"),
    )
    for label, key in keys:
        value = system_info.get(key)
        if isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        elif value is None:
            rendered = "Not detected"
        else:
            rendered = str(value)
        table.add_row(label, rendered)
    return Panel(table, title="System Information", border_style="bright_black", box=box.ROUNDED)


def results_table(report: HealthReport) -> Table:
    """Render all check results."""

    table = Table(
        title="Checks",
        expand=True,
        border_style="bright_black",
        header_style="bold bright_white",
        box=box.SIMPLE_HEAVY,
    )
    table.add_column("Status", no_wrap=True, width=10)
    table.add_column("Check", no_wrap=True, min_width=16)
    table.add_column("Category", no_wrap=True, width=10)
    table.add_column("Summary", ratio=3)
    table.add_column("Recommendation", ratio=2)

    for result in report.results:
        status_text = Text(
            f"{status_icon(result.status)} {result.status.value}",
            style=status_style(result.status),
        )
        table.add_row(
            status_text,
            result.title,
            result.category.value,
            result.summary,
            result.recommendation or "",
        )
    return table


def recommendations_panel(report: HealthReport) -> Panel:
    """Render actionable recommendations."""

    if not report.recommendations:
        text = Text(
            "No recommendations. Your development environment looks healthy.", style="success"
        )
        return Panel(text, title="Recommendations", border_style="green", box=box.ROUNDED)

    lines = Text()
    for index, recommendation in enumerate(report.recommendations, start=1):
        lines.append(f"{index}. ", style="muted")
        lines.append(recommendation)
        if index < len(report.recommendations):
            lines.append("\n")
    return Panel(lines, title="Recommendations", border_style="yellow", box=box.ROUNDED)


def compact_status(report: HealthReport) -> str:
    """Return a compact one-line summary for scripts."""

    summary = report.summary
    return (
        f"score={report.score} passed={summary.passed} "
        f"warnings={summary.warnings} failed={summary.failed}"
    )


def filter_results(report: HealthReport, category: CheckCategory | None) -> tuple[CheckResult, ...]:
    """Return results filtered by category for external UI consumers."""

    if category is None:
        return tuple(report.results)
    return tuple(result for result in report.results if result.category is category)


def _metric(label: str, value: str, style: str) -> Text:
    text = Text()
    text.append(f"{label}\n", style="muted")
    text.append(value, style=style)
    return text
