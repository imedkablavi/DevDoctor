"""Public console entry point with release hardening enabled."""

from __future__ import annotations

from devdoctor.cli import app
from devdoctor.hardening import apply_runtime_hardening, register_hardening_commands


def main() -> None:
    """Run DevDoctor with Atomic-safe runtime policy and extra support commands."""

    apply_runtime_hardening()
    register_hardening_commands(app)
    app()
