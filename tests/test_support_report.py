from __future__ import annotations

from devdoctor.support_report import render_support_markdown


def test_support_markdown_renders_scrubbed_diagnostic_fields() -> None:
    snapshot = {
        "platform": {
            "distribution": "Fedora Linux 42",
            "distribution_id": "fedora",
            "variant_id": "silverblue",
            "architecture": "x86_64",
            "kernel": "6.15.0",
            "python": "3.13.7",
            "session_type": "wayland",
            "shell": "bash",
            "atomic_host": True,
        },
        "package_managers": [
            {
                "id": "rpm-ostree",
                "installed": True,
                "version": "2026.8",
                "path_class": "system",
                "family": "system",
            }
        ],
        "manager_conflicts": [],
        "path": {"entry_count": 9, "contains_empty_entry": False},
        "privacy": {
            "hostname_included": False,
            "username_included": False,
            "environment_values_included": False,
            "raw_path_included": False,
        },
    }

    rendered = render_support_markdown(snapshot)

    assert "# DevDoctor support report" in rendered
    assert "Fedora Linux 42" in rendered
    assert "rpm-ostree" in rendered
    assert "raw PATH" in rendered
    assert "/home/" not in rendered


def test_support_markdown_neutralizes_markdown_control_delimiters() -> None:
    snapshot = {
        "platform": {
            "distribution": "Bad`value|column\nsecond-line",
            "distribution_id": "test",
        },
        "package_managers": [],
        "manager_conflicts": [],
        "path": {},
    }

    rendered = render_support_markdown(snapshot)

    assert "Bad'value\\|column second-line" in rendered
    assert "Bad`value" not in rendered
    assert "value|column" not in rendered
