"""Typed domain models for DevDoctor checks and reports."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypeAlias

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | Mapping[str, "JsonValue"] | Sequence["JsonValue"]


class CheckStatus(StrEnum):
    """Health state emitted by a check."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class CheckCategory(StrEnum):
    """Top-level category used for grouping results."""

    SYSTEM = "system"
    TOOL = "tool"
    NETWORK = "network"


@dataclass(frozen=True, slots=True)
class CheckResult:
    """A normalized result returned by every isolated check."""

    id: str
    title: str
    category: CheckCategory
    status: CheckStatus
    summary: str
    details: Mapping[str, JsonValue] = field(default_factory=dict)
    recommendation: str | None = None
    weight: int = 1

    @classmethod
    def ok(
        cls,
        *,
        id: str,
        title: str,
        category: CheckCategory,
        summary: str,
        details: Mapping[str, JsonValue] | None = None,
        recommendation: str | None = None,
        weight: int = 1,
    ) -> CheckResult:
        """Create a passing check result."""

        return cls(
            id=id,
            title=title,
            category=category,
            status=CheckStatus.PASS,
            summary=summary,
            details=details or {},
            recommendation=recommendation,
            weight=weight,
        )

    @classmethod
    def warning(
        cls,
        *,
        id: str,
        title: str,
        category: CheckCategory,
        summary: str,
        details: Mapping[str, JsonValue] | None = None,
        recommendation: str | None = None,
        weight: int = 1,
    ) -> CheckResult:
        """Create a warning check result."""

        return cls(
            id=id,
            title=title,
            category=category,
            status=CheckStatus.WARNING,
            summary=summary,
            details=details or {},
            recommendation=recommendation,
            weight=weight,
        )

    @classmethod
    def failure(
        cls,
        *,
        id: str,
        title: str,
        category: CheckCategory,
        summary: str,
        details: Mapping[str, JsonValue] | None = None,
        recommendation: str | None = None,
        weight: int = 1,
    ) -> CheckResult:
        """Create a failing check result."""

        return cls(
            id=id,
            title=title,
            category=category,
            status=CheckStatus.FAIL,
            summary=summary,
            details=details or {},
            recommendation=recommendation,
            weight=weight,
        )

    @property
    def passed(self) -> bool:
        """Return whether the check passed."""

        return self.status is CheckStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        """Convert the check result to JSON-serializable data."""

        return {
            "id": self.id,
            "title": self.title,
            "category": self.category.value,
            "status": self.status.value,
            "summary": self.summary,
            "details": self.details,
            "recommendation": self.recommendation,
            "weight": self.weight,
        }


CheckCallable: TypeAlias = Callable[[], CheckResult]


@dataclass(frozen=True, slots=True)
class ReportSummary:
    """Aggregated status counts for a health report."""

    passed: int
    warnings: int
    failed: int
    total: int

    def to_dict(self) -> dict[str, int]:
        """Convert the summary to JSON-serializable data."""

        return {
            "passed": self.passed,
            "warnings": self.warnings,
            "failed": self.failed,
            "total": self.total,
        }


@dataclass(frozen=True, slots=True)
class HealthReport:
    """Final report produced by a DevDoctor run."""

    generated_at: datetime
    duration_seconds: float
    score: int
    results: tuple[CheckResult, ...]
    recommendations: tuple[str, ...]

    @property
    def summary(self) -> ReportSummary:
        """Count checks by status."""

        passed = sum(1 for result in self.results if result.status is CheckStatus.PASS)
        warnings = sum(1 for result in self.results if result.status is CheckStatus.WARNING)
        failed = sum(1 for result in self.results if result.status is CheckStatus.FAIL)
        return ReportSummary(
            passed=passed,
            warnings=warnings,
            failed=failed,
            total=len(self.results),
        )

    @property
    def system_info(self) -> Mapping[str, JsonValue]:
        """Return system-oriented details in a compact dictionary."""

        system_results = [
            result for result in self.results if result.category is CheckCategory.SYSTEM
        ]
        info: dict[str, JsonValue] = {}
        for result in system_results:
            for key, value in result.details.items():
                if key not in info:
                    info[key] = value
        return info

    def to_dict(self) -> dict[str, Any]:
        """Convert the report to JSON-serializable data."""

        return {
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "duration_seconds": round(self.duration_seconds, 3),
            "score": self.score,
            "summary": self.summary.to_dict(),
            "system_info": self.system_info,
            "recommendations": list(self.recommendations),
            "results": [result.to_dict() for result in self.results],
        }
