from __future__ import annotations

from types import SimpleNamespace

import pytest

from devdoctor import project_diagnostics


@pytest.mark.parametrize(
    ("installed", "constraint", "expected"),
    [
        ("Python 3.13.7", ">=3.11", True),
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


def test_discovery_reads_common_project_manifests(tmp_path: object) -> None:
    root = tmp_path
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nrequires-python = ">=3.12"\n',
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        '{"engines":{"node":">=22","npm":">=10"},"packageManager":"pnpm@9.15.0"}',
        encoding="utf-8",
    )
    (root / "Cargo.toml").write_text(
        '[package]\nname = "demo"\nrust-version = "1.82"\n',
        encoding="utf-8",
    )
    (root / "go.mod").write_text("module example.test/demo\n\ngo 1.23\n", encoding="utf-8")
    (root / ".tool-versions").write_text("python 3.12.6\nnodejs 22.11.0\n", encoding="utf-8")
    (root / "mise.toml").write_text('[tools]\nterraform = "1.9"\n', encoding="utf-8")
    (root / "devbox.json").write_text(
        '{"packages":["python@3.12","nodejs@22","ripgrep@latest"]}',
        encoding="utf-8",
    )

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(root)
    triples = {(item.tool_id, item.source, item.constraint) for item in requirements}

    assert ("python", "pyproject.toml", ">=3.12") in triples
    assert ("node", "package.json", ">=22") in triples
    assert ("npm", "package.json", ">=10") in triples
    assert ("pnpm", "package.json", "9.15.0") in triples
    assert ("rust", "Cargo.toml", ">=1.82") in triples
    assert ("go", "go.mod", ">=1.23") in triples
    assert ("terraform", "mise.toml", "1.9") in triples
    assert ("python", "devbox.json", "3.12") in triples
    assert "devbox.json" in sources
    assert warnings == ()


def test_discovery_refuses_symlinked_manifests(tmp_path: object) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside-package.json"
    outside.write_text('{"engines":{"node":">=99"}}', encoding="utf-8")
    (root / "package.json").symlink_to(outside)

    requirements, sources, warnings = project_diagnostics.discover_project_requirements(root)

    assert requirements == ()
    assert sources == ()
    assert any("symlinked manifests are not followed" in warning for warning in warnings)


def test_diagnose_project_marks_version_mismatch_and_missing_tool(
    tmp_path: object,
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


def test_project_json_does_not_include_absolute_root_path(tmp_path: object) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")

    report = project_diagnostics.diagnose_project(tmp_path)
    rendered = str(report.to_dict())

    assert str(tmp_path) not in rendered
    assert report.project_name == tmp_path.name
