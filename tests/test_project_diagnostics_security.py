from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from devdoctor import project_diagnostics


def test_constraint_normalization_removes_control_characters() -> None:
    normalized = project_diagnostics._normalize_constraint("\x1b[31m>=22\x1b[0m")

    assert normalized is not None
    assert "\x1b" not in normalized
    assert "\n" not in normalized
    assert len(normalized) <= project_diagnostics._MAX_CONSTRAINT_CHARS
    assert project_diagnostics.version_satisfies("22.0.0", normalized) is None


def test_oversized_constraint_becomes_bounded_unknown_expression() -> None:
    normalized = project_diagnostics._normalize_constraint("x" * 10_000)

    assert normalized == "<unsupported: constraint too long>"
    assert project_diagnostics.version_satisfies("22.0.0", normalized) is None


def test_project_name_is_bounded_and_control_safe(tmp_path: Path) -> None:
    project = tmp_path / "bad\x1b[31m-project"
    project.mkdir()

    report = project_diagnostics.diagnose_project(project)

    assert "\x1b" not in report.project_name
    assert len(report.project_name) <= 120


def test_detected_version_is_sanitized_before_terminal_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.12"\n',
        encoding="utf-8",
    )
    python_spec = SimpleNamespace(id="python")
    monkeypatch.setattr(
        project_diagnostics,
        "get_bootstrap_tools",
        lambda: (python_spec,),
    )
    monkeypatch.setattr(
        project_diagnostics,
        "bootstrap_inventory",
        lambda include_ids: SimpleNamespace(
            detections=(
                SimpleNamespace(
                    spec=python_spec,
                    installed=True,
                    version="3.13.7\x1b[31m",
                ),
            )
        ),
    )

    report = project_diagnostics.diagnose_project(tmp_path)
    rendered = project_diagnostics.render_project_report(report)

    assert report.checks[0].status == "ready"
    assert "\x1b" not in rendered
