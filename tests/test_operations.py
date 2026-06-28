from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from devdoctor.operations import OperationLogRecord, append_operation_log


def test_append_operation_log_writes_json_line(tmp_path: Path) -> None:
    path = tmp_path / "operations.log"
    record = OperationLogRecord(
        timestamp=datetime(2026, 6, 28, tzinfo=UTC),
        operation="install",
        selected_package_manager="apt",
        command=("sudo", "apt", "install", "git"),
        exit_code=0,
        duration_seconds=1.2345,
        verification_command=("git", "--version"),
        verification_exit_code=0,
        verification_output="git version 2.45.0",
    )

    append_operation_log(path, record)
    parsed = json.loads(path.read_text(encoding="utf-8"))

    assert parsed["operation"] == "install"
    assert parsed["selected_package_manager"] == "apt"
    assert parsed["command_text"] == "sudo apt install git"
    assert parsed["exit_code"] == 0
    assert parsed["duration_seconds"] == 1.234
    assert parsed["verification_command"] == ["git", "--version"]
