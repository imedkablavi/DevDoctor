"""Health scoring for DevDoctor reports."""

from __future__ import annotations

from collections.abc import Iterable

from devdoctor.models import CheckResult, CheckStatus


def calculate_health_score(results: Iterable[CheckResult]) -> int:
    """Calculate a 0-100 health score from check statuses and weights."""

    penalty = 0
    for result in results:
        weight = max(result.weight, 0)
        if result.status is CheckStatus.FAIL:
            penalty += 6 + (4 * weight)
        elif result.status is CheckStatus.WARNING:
            penalty += 2 * weight
    return max(0, min(100, 100 - penalty))


def collect_recommendations(results: Iterable[CheckResult]) -> tuple[str, ...]:
    """Collect unique actionable recommendations from non-passing checks."""

    recommendations: list[str] = []
    seen: set[str] = set()
    for result in results:
        if result.status is CheckStatus.PASS or not result.recommendation:
            continue
        if result.recommendation in seen:
            continue
        seen.add(result.recommendation)
        recommendations.append(result.recommendation)
    return tuple(recommendations)
