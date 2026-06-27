"""Rich theme and status styling."""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

from devdoctor.models import CheckStatus


def create_console(*, no_color: bool = False) -> Console:
    """Create a themed Rich console."""

    return Console(theme=devdoctor_theme(), no_color=no_color, color_system="auto")


def devdoctor_theme() -> Theme:
    """Return the DevDoctor Rich color palette."""

    return Theme(
        {
            "brand": "bold bright_cyan",
            "brand.mark": "bold cyan",
            "tagline": "bright_black",
            "section": "bold white",
            "muted": "bright_black",
            "success": "bold #34D399",
            "warning": "bold yellow",
            "error": "bold #FB7185",
            "score.high": "bold #34D399",
            "score.medium": "bold yellow",
            "score.low": "bold #FB7185",
            "path": "bright_cyan",
        }
    )


def status_icon(status: CheckStatus) -> str:
    """Return the UI icon for a check status."""

    return {
        CheckStatus.PASS: "✓",
        CheckStatus.WARNING: "⚠",
        CheckStatus.FAIL: "✕",
    }[status]


def status_style(status: CheckStatus) -> str:
    """Return the Rich style for a check status."""

    return {
        CheckStatus.PASS: "success",
        CheckStatus.WARNING: "warning",
        CheckStatus.FAIL: "error",
    }[status]


def score_style(score: int) -> str:
    """Return the Rich style for a health score."""

    if score >= 85:
        return "score.high"
    if score >= 65:
        return "score.medium"
    return "score.low"
