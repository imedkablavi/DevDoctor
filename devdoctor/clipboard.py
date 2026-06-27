"""Clipboard integration helpers."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClipboardResult:
    """Result of a clipboard copy attempt."""

    copied: bool
    message: str


def copy_to_clipboard(text: str) -> ClipboardResult:
    """Copy text to the system clipboard using available Linux clipboard tools."""

    commands = (
        ("wl-copy", ("wl-copy",)),
        ("xclip", ("xclip", "-selection", "clipboard")),
        ("xsel", ("xsel", "--clipboard", "--input")),
        ("pbcopy", ("pbcopy",)),
    )
    for executable, command in commands:
        if shutil.which(executable):
            try:
                subprocess.run(
                    command,
                    input=text,
                    text=True,
                    check=True,
                    timeout=5,
                    capture_output=True,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return ClipboardResult(False, f"Clipboard copy failed: {exc}")
            return ClipboardResult(True, f"Copied report with {executable}.")
    return ClipboardResult(
        False,
        "No clipboard tool found. Install wl-clipboard, xclip, or xsel.",
    )
