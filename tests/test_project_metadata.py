from __future__ import annotations

import re
import tomllib
from pathlib import Path

from devdoctor import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_project_version_matches_package_version() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["version"] == __version__


def test_distribution_name_and_console_script_are_stable() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["name"] == "devdoctor-workstation"
    assert metadata["project"]["scripts"] == {"devdoctor": "devdoctor.entrypoint:main"}


def test_local_markdown_links_resolve() -> None:
    markdown_files = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / "MIGRATION_GUIDE.md",
        ROOT / "RELEASE_READINESS.md",
        ROOT / "RELEASE_PROCESS.md",
        ROOT / "ROADMAP.md",
        ROOT / "SECURITY.md",
        ROOT / "SUPPORT.md",
        *sorted((ROOT / "docs").glob("*.md")),
        *sorted((ROOT / "examples").glob("*.md")),
    ]
    missing: list[str] = []
    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8")
        for match in re.finditer(r"!?\[[^\]]+\]\(([^)]+)\)", text):
            target = match.group(1).split("#", 1)[0]
            if not target or re.match(r"^[a-z]+://", target):
                continue
            path = (markdown_file.parent / target).resolve()
            if not path.exists():
                missing.append(f"{markdown_file.relative_to(ROOT)} -> {target}")

    assert missing == []
