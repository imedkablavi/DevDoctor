"""Public console entry point with release hardening enabled."""

from __future__ import annotations

from devdoctor.atomic_planning import apply_atomic_planning_patch
from devdoctor.cli import app
from devdoctor.fallback_planning import apply_fallback_planning_patch
from devdoctor.hardening import apply_runtime_hardening, register_hardening_commands
from devdoctor.path_conflicts import register_path_conflict_command
from devdoctor.repair_transactions import register_repair_transaction_commands


def main() -> None:
    """Run DevDoctor with Atomic-safe runtime policy and extra support commands."""

    apply_atomic_planning_patch()
    apply_fallback_planning_patch()
    apply_runtime_hardening()
    register_hardening_commands(app)
    register_path_conflict_command(app)
    register_repair_transaction_commands(app)
    app()
