"""Application paths managed through platformdirs."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_state_path


def state_dir() -> Path:
    """Return DevDoctor's per-user state directory."""

    return user_state_path(appname="devdoctor", appauthor=False, ensure_exists=True)


def latest_report_path() -> Path:
    """Return the path used for the optional latest JSON report cache."""

    return state_dir() / "latest-report.json"
