from __future__ import annotations

import json
import os
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

import pytest

from devdoctor import project_diagnostics
from devdoctor.utils import CommandResult


@pytest.mark.parametrize(
    ("installed", "constraint", "expected"),
    [
        ("Python 3.13.7", ">=3.11", True),
        ("Python 3.13.7", ">=3.11,!=3.12.0", True),
        ("Python 3.12.0", ">=3.11,!=3.12.0", False),
        ("Python 3.12.4", ">=3.11,!=3.12.*", False),
        ("Python 3.13.0", ">=3.11,!=3.12.*", True),
        ("Python 3.11.9", "~=3.11", True),
        ("Python 4.0.0", "~=3.11", False),
        ("Python 3.11.8", "~=3.11.2", True),
        ("Python 3.12.0", "~=3.11.2", False),
        ("v22.4.1", ">=20 <23", True),
        ("v18.19.0", ">=20 <23", False),
        ("9.12.0", "9.12.0", True),
        ("9.13.0", "9.12.0", False),
        ("22.7.0", "22.x", True),
        ("23.0.0", "22.x", False),
        ("20.12.2", "^20.10.0", True),
        ("21.0.0", "^20.10.0", False),
        ("3.12.4", "~3.12", True),
        ("3.13.0", "~3.12", False),
        ("22.0.0", ">=18 || ^22", True),
        ("22.0.0", "18 - 20", None),
        (None, ">=3.11", None),
    ],
)
def test_version_satisfies_common_project_constraints(
    installed: str | None,
    constraint: str,
    expected: bool | None,
) -> None:
    assert project_diagnostics.version_satisfies(installed, constraint) is expected


def test_version_comparison_ignores_terminal_escape_sequences() -> None:
    colored = "\x1b[31mPython 3.13.7\x1b[0m"

    assert project_diagnostics.version_satisfies(colored, ">=3.11") is True
    assert project_diagnostics.version_satisfies(colored, ">=31") is False


def test_unknown_declared_constraint_is_blocking_by_default() -> None:
    report = project_diagnostics.ProjectReport(
        project_name="demo",
        sources=("package.json",),
        checks=(
            project_diagnostics.ProjectCheck(
                tool_id="node",
                source="package.json",
                constraint="workspace:*",
                installed=True,
                installed_version="22.0.0",
                status="unknown",
                message="not safely comparable",
            ),
        ),
        warnings=(),
    )

    assert report.blocking is True


def test_discovery_reads_common_project_manifests(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.12"\n',
        encoding="utf-8",
    )
    package = {
        "engines": {"node": ">=22", "npm": ">=10"},
        "packageManager": "pnpm@9.15.0+sha512-example",
    }
    (tmp_path / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "demo"\nrust-version = "1.82"\n',
        encoding="utf-8",
    )
    (tmp_path / "go.mod").write_text(
        "module example.test/demo\n\ngo 1.23\n",
        encoding="utf-8",
    )
    (tmp_path / ".tool-versions").write_text(
        "python 3.12.6\nnodejs 22.11.0\n",
        encoding="utf-8",
    )
    (tmp_path / "mise.toml").write_text(
        '[tools]\nterraform = "1.9"\n',
        encoding="utf-8",
    )
    (tmp_path / "devbox.json").write_text(
        '{"packages":["python@3.12","nodejs@22","ripgrep@latest"]}',
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\n", encoding="utf-8")
    (tmp_path / "composer.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "pom.xml").write_text("<project/>\n", encoding="utf-8")

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(tmp_path)
    triples = {(item.tool_id, item.source, item.constraint) for item in requirements}

    assert ("python", "pyproject.toml", ">=3.12") in triples
    assert ("node", "package.json", ">=22") in triples
    assert ("npm", "package.json", ">=10") in triples
    assert ("pnpm", "package.json", "9.15.0") in triples
    assert ("rustc", "Cargo.toml", ">=1.82") in triples
    assert ("cargo", "Cargo.toml", None) in triples
    assert ("go", "go.mod", ">=1.23") in triples
    assert ("terraform", "mise.toml", "1.9") in triples
    assert ("python", "devbox.json", "3.12") in triples
    assert ("docker", "Dockerfile", None) in triples
    assert ("ruby", "Gemfile", None) in triples
    assert ("php", "composer.json", None) in triples
    assert ("java", "pom.xml", None) in triples
    assert "devbox.json" in sources
    assert warnings == ()


def test_presence_only_manifests_still_require_their_runtime(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n',
        encoding="utf-8",
    )
    (tmp_path / "Cargo.toml").write_text(
        '[package]\nname = "demo"\n',
        encoding="utf-8",
    )
    (tmp_path / "go.mod").write_text("module example.test/demo\n", encoding="utf-8")

    requirements, _, warnings = project_diagnostics.discover_project_requirements(tmp_path)
    triples = {(item.tool_id, item.source, item.constraint) for item in requirements}

    assert ("node", "package.json", None) in triples
    assert ("python", "pyproject.toml", None) in triples
    assert ("rustc", "Cargo.toml", None) in triples
    assert ("cargo", "Cargo.toml", None) in triples
    assert ("go", "go.mod", None) in triples
    assert warnings == ()


def test_discovery_never_executes_package_scripts(tmp_path: Path) -> None:
    marker = tmp_path / "must-not-exist"
    payload = {
        "scripts": {"postinstall": f"touch {marker}"},
        "engines": {"node": ">=22"},
    }
    (tmp_path / "package.json").write_text(json.dumps(payload), encoding="utf-8")

    requirements, _, warnings = project_diagnostics.discover_project_requirements(tmp_path)

    assert any(item.tool_id == "node" for item in requirements)
    assert warnings == ()
    assert not marker.exists()


def test_project_probe_excludes_project_local_executables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    marker = project / "executed"
    malicious = project / "node"
    malicious.write_text(f"#!/bin/sh\ntouch {marker}\necho v99.0.0\n", encoding="utf-8")
    malicious.chmod(0o755)
    (project / "package.json").write_text('{"engines":{"node":">=20"}}', encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.setenv("PATH", f".:{project}:{os.environ.get('PATH', '')}")

    node_spec = SimpleNamespace(id="node")
    monkeypatch.setattr(project_diagnostics, "get_bootstrap_tools", lambda: (node_spec,))

    def fake_inventory(include_ids: tuple[str, ...]) -> SimpleNamespace:
        resolved = project_diagnostics.shutil.which("node")
        if resolved is not None:
            assert not project_diagnostics._inside(Path(resolved).resolve(), project.resolve())
        return SimpleNamespace(
            detections=(SimpleNamespace(spec=node_spec, installed=False, version=None),)
        )

    monkeypatch.setattr(project_diagnostics, "bootstrap_inventory", fake_inventory)

    project_diagnostics.diagnose_project(project)

    assert not marker.exists()


def test_project_python_requirement_falls_back_to_safe_python3(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.11"\n',
        encoding="utf-8",
    )
    python_spec = SimpleNamespace(id="python")
    monkeypatch.setattr(project_diagnostics, "get_bootstrap_tools", lambda: (python_spec,))
    monkeypatch.setattr(
        project_diagnostics,
        "bootstrap_inventory",
        lambda include_ids: SimpleNamespace(
            detections=(SimpleNamespace(spec=python_spec, installed=False, version=None),)
        ),
    )
    monkeypatch.setattr(
        project_diagnostics.shutil,
        "which",
        lambda name, mode=os.F_OK | os.X_OK, path=None: "/usr/bin/python3"
        if name == "python3"
        else None,
    )
    monkeypatch.setattr(
        project_diagnostics,
        "run_command",
        lambda command, timeout=5: CommandResult(
            command=tuple(command),
            returncode=0,
            stdout="Python 3.12.4\n",
            stderr="",
            duration_seconds=0.01,
        ),
    )

    report = project_diagnostics.diagnose_project(tmp_path)

    assert report.checks[0].tool_id == "python"
    assert report.checks[0].status == "ready"
    assert report.checks[0].installed_version == "3.12.4"


def test_discovery_refuses_symlinked_manifests(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside-package.json"
    outside.write_text('{"engines":{"node":">=99"}}', encoding="utf-8")
    (root / "package.json").symlink_to(outside)

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(root)

    assert requirements == ()
    assert sources == ()
    assert any("symlinked manifests are not followed" in warning for warning in warnings)


def test_discovery_refuses_non_regular_manifest(tmp_path: Path) -> None:
    fifo = tmp_path / "package.json"
    os.mkfifo(fifo)

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(tmp_path)

    assert requirements == ()
    assert sources == ()
    assert any("non-regular manifests are not read" in warning for warning in warnings)


def test_discovery_refuses_oversized_manifest(tmp_path: Path) -> None:
    oversized = " " * (project_diagnostics._MAX_MANIFEST_BYTES + 1)
    (tmp_path / "package.json").write_text(oversized, encoding="utf-8")

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(tmp_path)

    assert requirements == ()
    assert sources == ()
    assert any("manifest exceeds" in warning for warning in warnings)


def test_invalid_and_excessively_nested_manifests_become_warnings(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("[" * 2_000 + "]" * 2_000, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(tmp_path)

    assert requirements == ()
    assert set(sources) == {"package.json", "pyproject.toml"}
    assert any("package.json: invalid or excessively nested JSON" in item for item in warnings)
    assert any("pyproject.toml: invalid or excessively nested TOML" in item for item in warnings)


def test_requirement_count_is_bounded(tmp_path: Path) -> None:
    packages = [f"python@3.{index}" for index in range(project_diagnostics._MAX_REQUIREMENTS * 3)]
    (tmp_path / "devbox.json").write_text(
        json.dumps({"packages": packages}),
        encoding="utf-8",
    )

    requirements, _, warnings = project_diagnostics.discover_project_requirements(tmp_path)

    assert len(requirements) == project_diagnostics._MAX_REQUIREMENTS
    assert any("requirement limit reached" in warning for warning in warnings)


def test_large_supported_manifest_has_bounded_python_peak_memory(tmp_path: Path) -> None:
    payload = {"engines": {"node": ">=22"}, "padding": "x" * 900_000}
    (tmp_path / "package.json").write_text(json.dumps(payload), encoding="utf-8")

    tracemalloc.start()
    try:
        requirements, _, warnings = project_diagnostics.discover_project_requirements(tmp_path)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert any(item.tool_id == "node" for item in requirements)
    assert warnings == ()
    assert peak < 16 * 1024 * 1024


def test_diagnose_project_marks_version_mismatch_and_missing_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=99"\n',
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"engines":{"node":">=22"}}',
        encoding="utf-8",
    )

    python_spec = SimpleNamespace(id="python")
    node_spec = SimpleNamespace(id="node")
    monkeypatch.setattr(
        project_diagnostics,
        "get_bootstrap_tools",
        lambda: (python_spec, node_spec),
    )
    monkeypatch.setattr(
        project_diagnostics,
        "bootstrap_inventory",
        lambda include_ids: SimpleNamespace(
            detections=(
                SimpleNamespace(spec=python_spec, installed=True, version="3.13.7"),
                SimpleNamespace(spec=node_spec, installed=False, version=None),
            )
        ),
    )

    report = project_diagnostics.diagnose_project(tmp_path)
    by_tool = {check.tool_id: check for check in report.checks}

    assert by_tool["python"].status == "mismatch"
    assert by_tool["node"].status == "missing"
    assert report.blocking is True


def test_project_json_does_not_include_absolute_root_path(tmp_path: Path) -> None:
    report = project_diagnostics.diagnose_project(tmp_path)
    rendered = str(report.to_dict())

    assert str(tmp_path) not in rendered
    assert report.project_name == tmp_path.name
