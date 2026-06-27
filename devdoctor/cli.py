"""Typer command-line interface for DevDoctor."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from devdoctor import __version__
from devdoctor.doctor import DevDoctor
from devdoctor.exporters.html import write_html_report
from devdoctor.exporters.json import render_json, write_json_report
from devdoctor.exporters.markdown import write_markdown_report
from devdoctor.exporters.pdf import write_pdf_report
from devdoctor.models import HealthReport
from devdoctor.paths import latest_report_path
from devdoctor.ui.logo import banner
from devdoctor.ui.progress import create_progress
from devdoctor.ui.table import compact_status, report_group
from devdoctor.ui.theme import create_console

app = typer.Typer(
    name="devdoctor",
    help=(
        "[bold cyan]DevDoctor[/bold cyan] diagnoses Linux development workstations "
        "through an interactive dashboard or script-friendly reports."
    ),
    epilog=(
        "Examples:\n"
        "  devdoctor\n"
        "  devdoctor --classic\n"
        "  devdoctor --quiet --fail-under 75\n"
        "  devdoctor --json --network-timeout 2\n\n"
        "Dashboard shortcuts: / search, Ctrl+R refresh, Ctrl+E export, Ctrl+F auto fix, Q quit."
    ),
    add_completion=False,
    invoke_without_command=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the DevDoctor version and exit."),
    ] = False,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Print the report as JSON instead of Rich output."),
    ] = False,
    json_file: Annotated[
        Path | None,
        typer.Option("--json-file", help="Write a JSON report to this path."),
    ] = None,
    html_file: Annotated[
        Path | None,
        typer.Option("--html-file", help="Write a standalone HTML report to this path."),
    ] = None,
    markdown_file: Annotated[
        Path | None,
        typer.Option("--markdown-file", help="Write a Markdown report to this path."),
    ] = None,
    pdf_file: Annotated[
        Path | None,
        typer.Option("--pdf-file", help="Write a compact PDF report to this path."),
    ] = None,
    save_latest: Annotated[
        bool,
        typer.Option(
            "--save-latest", help="Save the latest JSON report under the user state directory."
        ),
    ] = False,
    no_progress: Annotated[
        bool,
        typer.Option("--no-progress", help="Disable progress bars."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable terminal colors."),
    ] = False,
    network_timeout: Annotated[
        float,
        typer.Option(
            "--network-timeout", min=0.5, max=30.0, help="Network probe timeout in seconds."
        ),
    ] = 3.0,
    fail_under: Annotated[
        int | None,
        typer.Option(
            "--fail-under", min=0, max=100, help="Exit with code 1 if score is below this value."
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Print only a compact final status line."),
    ] = False,
    classic: Annotated[
        bool,
        typer.Option("--classic", help="Use the classic Rich report instead of the dashboard."),
    ] = False,
) -> None:
    """Open the dashboard, run the classic report, or export workstation health data."""

    console = create_console(no_color=no_color)
    if version:
        console.print(f"devdoctor {__version__}")
        raise typer.Exit(code=0)

    if ctx.invoked_subcommand is not None:
        return

    scripted_mode = any(
        (
            output_json,
            json_file is not None,
            html_file is not None,
            markdown_file is not None,
            pdf_file is not None,
            save_latest,
            quiet,
            no_progress,
            no_color,
            fail_under is not None,
            classic,
        )
    )
    if not scripted_mode and sys.stdin.isatty() and sys.stdout.isatty():
        from devdoctor.dashboard import run_dashboard

        run_dashboard(network_timeout=network_timeout)
        return

    report = _run_scan(
        network_timeout=network_timeout,
        output_json=output_json,
        no_progress=no_progress or quiet,
        show_banner=not quiet,
        console=console,
    )

    if json_file:
        written = write_json_report(report, json_file)
        if not output_json and not quiet:
            console.print(f"[success]JSON report written:[/success] [path]{written}[/path]")
    if html_file:
        written = write_html_report(report, html_file)
        if not output_json and not quiet:
            console.print(f"[success]HTML report written:[/success] [path]{written}[/path]")
    if markdown_file:
        written = write_markdown_report(report, markdown_file)
        if not output_json and not quiet:
            console.print(f"[success]Markdown report written:[/success] [path]{written}[/path]")
    if pdf_file:
        written = write_pdf_report(report, pdf_file)
        if not output_json and not quiet:
            console.print(f"[success]PDF report written:[/success] [path]{written}[/path]")
    if save_latest:
        write_json_report(report, latest_report_path())

    if output_json:
        sys.stdout.write(render_json(report))
        sys.stdout.write("\n")
    elif quiet:
        console.print(compact_status(report))
    else:
        console.print(report_group(report))

    if fail_under is not None and report.score < fail_under:
        if not output_json:
            Console(stderr=True).print(
                f"[bold red]Health score {report.score} is below threshold {fail_under}.[/bold red]"
            )
        raise typer.Exit(code=1)


def _run_scan(
    *,
    network_timeout: float,
    output_json: bool,
    no_progress: bool,
    show_banner: bool,
    console: Console,
) -> HealthReport:
    """Run checks with an optional Rich progress bar."""

    doctor = DevDoctor.default(network_timeout=network_timeout)
    if show_banner and not output_json:
        console.print(banner(__version__))

    if output_json or no_progress:
        return doctor.run()

    with create_progress(console) as progress:
        task_id = progress.add_task("Starting checks", total=len(doctor.checks))

        def update(description: str, index: int, total: int) -> None:
            progress.update(task_id, description=description, completed=index - 1, total=total)

        report = doctor.run(progress=update)
        progress.update(task_id, description="Complete", completed=len(doctor.checks))
    return report
