"""Python runtime checks."""

from __future__ import annotations

import sys

from devdoctor.models import CheckCategory, CheckResult


def check_python() -> CheckResult:
    """Validate the active Python runtime."""

    version = sys.version_info
    details = {
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "implementation": sys.implementation.name,
        "required_version": "3.11+",
    }
    if version < (3, 11):
        return CheckResult.failure(
            id="tool.python",
            title="Python",
            category=CheckCategory.TOOL,
            summary=f"Python {details['python_version']} is older than the supported runtime.",
            details=details,
            recommendation="Install Python 3.11 or newer and run DevDoctor with that interpreter.",
            weight=4,
        )
    return CheckResult.ok(
        id="tool.python",
        title="Python",
        category=CheckCategory.TOOL,
        summary=f"Python {details['python_version']} is available.",
        details=details,
        weight=4,
    )
