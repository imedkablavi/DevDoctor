from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime

import pytest
from textual.widgets import Input

import devdoctor.dashboard as dashboard_module
from devdoctor.actions import auto_fix_plans
from devdoctor.dashboard import DevDoctorDashboard
from devdoctor.doctor import create_report
from devdoctor.models import CheckCategory, CheckResult


def test_dashboard_search_exact_tool_opens_tool_detail_target() -> None:
    app = DevDoctorDashboard(network_timeout=0.5)
    app.report = create_report(
        results=(
            CheckResult.warning(
                id="tool.docker",
                title="Docker",
                category=CheckCategory.TOOL,
                summary="missing",
                details={"tool": "docker"},
            ),
        ),
        duration_seconds=0.1,
        generated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    assert app.find_search_target("docker") == "tool:tool.docker"
    assert app.find_search_target("doc") == "containers"
    assert app.find_search_target("d") is None


def test_auto_fix_does_not_suggest_install_for_installed_warning() -> None:
    result = CheckResult.warning(
        id="tool.docker",
        title="Docker",
        category=CheckCategory.TOOL,
        summary="Docker daemon is not reachable.",
        details={"installed": True, "path": "/usr/bin/docker", "daemon_accessible": False},
    )

    assert auto_fix_plans((result,)) == ()


def test_dashboard_render_worker_does_not_cancel_scan_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = create_report(
        results=(
            CheckResult.ok(
                id="system.os",
                title="Linux Distribution",
                category=CheckCategory.SYSTEM,
                summary="supported",
            ),
            CheckResult.warning(
                id="tool.docker",
                title="Docker",
                category=CheckCategory.TOOL,
                summary="missing",
                details={"tool": "docker"},
            ),
        ),
        duration_seconds=0.1,
        generated_at=datetime(2026, 6, 28, tzinfo=UTC),
    )

    class FakeDoctor:
        def run(self) -> object:
            time.sleep(0.15)
            return report

    monkeypatch.setattr(
        dashboard_module.DevDoctor,
        "default",
        classmethod(lambda cls, network_timeout=3.0: FakeDoctor()),
    )

    async def exercise() -> None:
        app = DevDoctorDashboard(network_timeout=0.5, refresh_interval=9999)
        async with app.run_test(size=(80, 24)) as pilot:
            deadline = asyncio.get_running_loop().time() + 4
            while app.report is None and asyncio.get_running_loop().time() < deadline:
                await pilot.pause(0.05)
            assert app.report is report
            assert app.last_scan_label != "Scan failed"
            await pilot.press("/")
            search = app.query_one("#search", Input)
            assert search.value == ""
            await pilot.press("d", "o", "c")
            await pilot.pause(0.05)
            assert app.selected_page == "containers"
            await pilot.press("ctrl+e")
            await pilot.pause(0.05)
            assert app.selected_page == "reports"

    asyncio.run(exercise())
