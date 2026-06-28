"""Structured operation logging for commands that change the workstation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from devdoctor.models import JsonValue


@dataclass(frozen=True, slots=True)
class OperationLogRecord:
    """One JSON Lines operation log record."""

    timestamp: datetime
    operation: str
    command: tuple[str, ...]
    exit_code: int
    duration_seconds: float
    selected_package_manager: str | None = None
    verification_command: tuple[str, ...] | None = None
    verification_exit_code: int | None = None
    verification_output: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Convert the record to JSON data."""

        return {
            "timestamp": self.timestamp.astimezone(UTC).isoformat(),
            "operation": self.operation,
            "selected_package_manager": self.selected_package_manager,
            "command": list(self.command),
            "command_text": " ".join(self.command),
            "exit_code": self.exit_code,
            "duration_seconds": round(self.duration_seconds, 3),
            "verification_command": (
                list(self.verification_command) if self.verification_command else None
            ),
            "verification_exit_code": self.verification_exit_code,
            "verification_output": self.verification_output,
        }


def append_operation_log(path: Path, record: OperationLogRecord) -> None:
    """Append one operation record as JSON Lines."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record.to_dict(), sort_keys=True))
        file.write("\n")
