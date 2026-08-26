from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from devdoctor import project_diagnostics


@pytest.mark.parametrize(
    ("installed", "constraint", "expected"),
    [
        ("Python 3.13.7", ">=3.11", True),
        ("Python 3.13.7", ">=3.11,!=3.12.0", True),
        ("Python 3.12.0", ">=3.11,!=3.12.0", False),
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


def test_discovery_reads_common_project_manifests(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.12"\n',
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        "{"
        '"engines":{"node":">=22","npm":">=10"},'
        '"packageManager":"pnpm@9.15.0+sha512-example"'
        "}",
        encoding="utf-8",
    )
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

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(
        tmp_path
    )
    triples = {(item.tool_id, item.source, item.constraint) for item in requirements}

    assert ("python", "pyproject.toml", ">=3.12") in triples
    assert ("node", "package.json", ">=22") in triples
    assert ("npm", "package.json", ">=10") in triples
    assert ("pnpm", "package.json", "9.15.0") in triples
    assert ("rust", "Cargo.toml", ">=1.82") in triples
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
    (tmp_path / "go.mod").write_text(
        "module example.test/demo\n",
        encoding="utf-8",
    )

    requirements, _, warnings = project_diagnostics.discover_project_requirements(tmp_path)
    triples = {(item.tool_id, item.source, item.constraint) for item in requirements}

    assert ("node", "package.json", None) in triples
    assert ("python", "pyproject.toml", None) in triples
    assert ("rust", "Cargo.toml", None) in triples
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


def test_discovery_refuses_oversized_manifest(tmp_path: Path) -> None:
    oversized = " " * (project_diagnostics._MAX_MANIFEST_BYTES + 1)
    (tmp_path / "package.json").write_text(oversized, encoding="utf-8")

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(tmp_path)

    assert requirements == ()
    assert sources == ()
    assert any("manifest exceeds" in warning for warning in warnings)


def test_invalid_manifests_become_warnings(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{not-json", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project\n", encoding="utf-8")

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(tmp_path)

    assert requirements == ()
    assert set(sources) == {"package.json", "pyproject.toml"}
    assert "package.json: invalid JSON" in warnings
    assert "pyproject.toml: invalid TOML" in warnings


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
    assert "MISMATCH" in project_diagnostics.render_project_report(report)
    assert "MISSING" in project_diagnostics.render_project_report(report)


def test_project_json_does_not_include_absolute_root_path(tmp_path: Path) -> None:
    report = project_diagnostics.diagnose_project(tmp_path)
    rendered = str(report.to_dict())

    assert str(tmp_path) not in rendered
    assert report.project_name == tmp_path.name
