"""Execution orchestration for DevDoctor checks."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from devdoctor.checks import get_all_checks
from devdoctor.models import CheckCallable, CheckCategory, CheckResult, HealthReport
from devdoctor.scoring import calculate_health_score, collect_recommendations

ProgressCallback = Callable[[str, int, int], None]


@dataclass(frozen=True, slots=True)
class DevDoctor:
    """Run checks in isolation and build a health report."""

    checks: Sequence[CheckCallable]

    @classmethod
    def default(cls, *, network_timeout: float = 3.0) -> DevDoctor:
        """Create a doctor with the standard Linux workstation checks."""

        return cls(checks=get_all_checks(network_timeout=network_timeout))

    def run(self, progress: ProgressCallback | None = None) -> HealthReport:
        """Run all checks and return the final report."""

        started_at = time.perf_counter()
        results: list[CheckResult] = []
        total = len(self.checks)

        for index, check in enumerate(self.checks, start=1):
            check_name = getattr(check, "__name__", check.__class__.__name__)
            if progress:
                progress(check_name.replace("_", " "), index, total)
            results.append(self._run_check(check, check_name))

        duration = time.perf_counter() - started_at
        return create_report(results=tuple(results), duration_seconds=duration)

    @staticmethod
    def _run_check(check: CheckCallable, check_name: str) -> CheckResult:
        """Execute one check and convert unexpected exceptions into failures."""

        try:
            return check()
        except Exception as exc:
            return CheckResult.failure(
                id=f"internal.{check_name}",
                title=check_name.replace("_", " ").title(),
                category=CheckCategory.SYSTEM,
                summary=f"Check failed unexpectedly: {exc}",
                details={"exception": exc.__class__.__name__},
                recommendation="Open an issue with the failing check name and system details.",
                weight=1,
            )


def create_report(
    *,
    results: tuple[CheckResult, ...],
    duration_seconds: float,
    generated_at: datetime | None = None,
) -> HealthReport:
    """Build a report object from completed check results."""

    generated = generated_at or datetime.now(tz=UTC)
    return HealthReport(
        generated_at=generated,
        duration_seconds=duration_seconds,
        score=calculate_health_score(results),
        results=results,
        recommendations=collect_recommendations(results),
    )
