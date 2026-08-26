from __future__ import annotations

from pathlib import Path

import pytest

from devdoctor import path_analysis
from devdoctor.path_analysis import analyze_path, executable_paths


def test_path_analysis_reports_missing_duplicates_and_shadowing(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for directory in (first, second):
        executable = directory / "tool"
        executable.write_text("#!/bin/sh\n", encoding="utf-8")
        executable.chmod(0o755)

    missing = tmp_path / "missing"
    path_value = f"{first}:{first}:{missing}:{second}"

    analysis = analyze_path(path_value, executables=("tool",), home=tmp_path)

    kinds = {issue.kind for issue in analysis.issues}
    assert "duplicate_entry" in kinds
    assert "missing_directory" in kinds
    assert analysis.shadowed_executables[0].executable == "tool"
    assert analysis.shadowed_executables[0].primary_path == str(first / "tool")
    assert analysis.shadowed_executables[0].shadowed_paths == (str(second / "tool"),)


def test_path_analysis_reports_common_user_bin_not_exported(tmp_path: Path) -> None:
    local_bin = tmp_path / ".local/bin"
    local_bin.mkdir(parents=True)

    analysis = analyze_path(str(tmp_path), executables=(), home=tmp_path)

    assert any(
        issue.kind == "not_exported" and issue.path == str(local_bin) for issue in analysis.issues
    )


def test_executable_paths_reports_broken_symlink(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    link = bin_dir / "stale-tool"
    link.symlink_to(tmp_path / "missing-target")

    assert executable_paths("stale-tool", (str(bin_dir),)) == (str(link),)


def test_default_executable_paths_respects_primary_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    executable = bin_dir / "tool"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)

    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(path_analysis.shutil, "which", lambda _name: None)

    assert executable_paths("tool") == ()
    assert executable_paths("tool", (str(bin_dir),)) == (str(executable),)
