"""Startup banner rendering."""

from __future__ import annotations

from rich import box
from rich.align import Align
from rich.panel import Panel
from rich.text import Text


def banner(version: str) -> Panel:
    """Build the DevDoctor startup banner."""

    title = Text()
    title.append("◆ ", style="brand.mark")
    title.append("Dev", style="brand")
    title.append("Doctor", style="bold white")
    title.append(f"  v{version}", style="muted")

    body = Text()
    body.append_text(title)
    body.append("\nPrepare and repair Linux developer workstations.", style="tagline")
    body.append("\ninventory  -  install plans  -  profiles  -  exports", style="muted")
    return Panel(
        Align.center(body),
        border_style="bright_cyan",
        box=box.ROUNDED,
        padding=(1, 2),
        title="Workstation Bootstrap",
        subtitle="devdoctor",
    )
