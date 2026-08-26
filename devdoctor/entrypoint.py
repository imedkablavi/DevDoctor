"""Public console entry point with release hardening enabled."""

from __future__ import annotations

from devdoctor.atomic_planning import apply_atomic_planning_patch
from devdoctor.fallback_planning import apply_fallback_planning_patch


def main() -> None:
    """Run DevDoctor with planner policy installed before the CLI binds imports."""

    # cli.py imports planner functions directly from bootstrap. Install planner
    # wrappers first so every CLI alias receives the hardened implementation.
    apply_atomic_planning_patch()
    apply_fallback_planning_patch()

    from devdoctor.cli import app
    from devdoctor.hardening import apply_runtime_hardening, register_hardening_commands
    from devdoctor.path_conflicts import register_path_conflict_command
    from devdoctor.project_diagnostics import register_project_diagnostics_command
    from devdoctor.release_safety import apply_release_safety
    from devdoctor.repair_transactions import register_repair_transaction_commands

    apply_runtime_hardening()
    register_hardening_commands(app)
    register_path_conflict_command(app)
    register_repair_transaction_commands(app)
    register_project_diagnostics_command(app)
    apply_release_safety(app)
    app()
