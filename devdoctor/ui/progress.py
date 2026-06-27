"""Progress UI helpers."""

from __future__ import annotations

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn


def create_progress(console: Console) -> Progress:
    """Create the standard DevDoctor progress bar."""

    return Progress(
        SpinnerColumn("dots", style="bright_cyan"),
        TextColumn("[section]{task.description}"),
        BarColumn(bar_width=None, complete_style="#34D399", finished_style="#22D3EE"),
        TextColumn("[muted]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )
