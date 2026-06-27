from __future__ import annotations

from devdoctor.models import CheckCategory, CheckResult
from devdoctor.scoring import calculate_health_score, collect_recommendations


def test_health_score_penalizes_failures_more_than_warnings() -> None:
    results = (
        CheckResult.ok(
            id="ok",
            title="OK",
            category=CheckCategory.SYSTEM,
            summary="ok",
            weight=5,
        ),
        CheckResult.warning(
            id="warn",
            title="Warn",
            category=CheckCategory.TOOL,
            summary="warn",
            recommendation="Fix warning.",
            weight=2,
        ),
        CheckResult.failure(
            id="fail",
            title="Fail",
            category=CheckCategory.NETWORK,
            summary="fail",
            recommendation="Fix failure.",
            weight=4,
        ),
    )

    assert calculate_health_score(results) == 74


def test_health_score_is_clamped_to_zero() -> None:
    results = tuple(
        CheckResult.failure(
            id=f"fail-{index}",
            title="Failure",
            category=CheckCategory.NETWORK,
            summary="fail",
            weight=5,
        )
        for index in range(10)
    )

    assert calculate_health_score(results) == 0


def test_collect_recommendations_deduplicates_non_passing_results() -> None:
    results = (
        CheckResult.warning(
            id="warn-1",
            title="Warn 1",
            category=CheckCategory.TOOL,
            summary="warn",
            recommendation="Install the tool.",
        ),
        CheckResult.failure(
            id="fail-1",
            title="Fail 1",
            category=CheckCategory.TOOL,
            summary="fail",
            recommendation="Install the tool.",
        ),
        CheckResult.ok(
            id="ok",
            title="OK",
            category=CheckCategory.SYSTEM,
            summary="ok",
            recommendation="Ignored.",
        ),
    )

    assert collect_recommendations(results) == ("Install the tool.",)
