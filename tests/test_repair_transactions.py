from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from devdoctor import bootstrap, repair_transactions


def _inventory(recommendation: bootstrap.RepairRecommendation) -> bootstrap.BootstrapInventory:
    spec = bootstrap.ToolSpec(
        id="test-tool",
        title="Test Tool",
        category=bootstrap.BootstrapCategory.SYSTEM,
        executable="test-tool",
    )
    detection = bootstrap.ToolDetection(
        spec=spec,
        installed=True,
        executable_path="/usr/bin/test-tool",
        version="1.0",
        package_manager="rpm",
        package_name="test-tool-1.0",
        config_locations=(),
        alternate_paths=(),
        installation_method="system path",
        health=bootstrap.HealthState.WARNING,
        broken_installation=False,
        permission_issues=(),
        path_issues=(),
        missing_dependencies=(),
        dependency_status=(),
        repair_recommendations=(recommendation,),
        install_plan=None,
    )
    return bootstrap.BootstrapInventory(system={}, detections=(detection,), profiles=())


def test_collect_repair_actions_requires_known_rollback() -> None:
    without_rollback = bootstrap.RepairRecommendation(
        problem="Needs manual edit",
        reason="test",
        risk="low",
        command=("test-tool", "fix"),
        verification_command=("test-tool", "--version"),
        rollback_command=None,
    )
    with_rollback = bootstrap.RepairRecommendation(
        problem="Service stopped",
        reason="test",
        risk="medium",
        command=("sudo", "systemctl", "start", "docker"),
        verification_command=("docker", "info"),
        rollback_command=("sudo", "systemctl", "stop", "docker"),
    )

    assert repair_transactions.collect_repair_actions(_inventory(without_rollback)) == ()
    actions = repair_transactions.collect_repair_actions(_inventory(with_rollback))
    assert len(actions) == 1
    assert actions[0].rollback_command == ("sudo", "systemctl", "stop", "docker")


def test_rollback_allowlist_validates_complete_shape() -> None:
    assert repair_transactions._allowed_rollback_command(("rpm-ostree", "uninstall", "git"))
    assert repair_transactions._allowed_rollback_command(("sudo", "dnf", "remove", "git"))
    assert not repair_transactions._allowed_rollback_command(
        ("sudo", "dnf", "remove", "--assumeyes", "bash")
    )
    assert not repair_transactions._allowed_rollback_command(
        ("sudo", "apt", "remove", "git", "bash")
    )
    assert not repair_transactions._allowed_rollback_command(("sh", "-c", "rm -rf /"))
    assert not repair_transactions._allowed_rollback_command(("sudo", "bash", "script.sh"))


def test_rollback_package_must_match_catalog_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = bootstrap.ToolSpec(
        id="git",
        title="Git",
        category=bootstrap.BootstrapCategory.SYSTEM,
        executable="git",
        packages={"apt": "git"},
    )
    monkeypatch.setattr(repair_transactions.bootstrap, "get_bootstrap_tools", lambda: (spec,))

    assert repair_transactions._allowed_rollback_command(
        ("sudo", "apt", "remove", "git"), tool_id="git"
    )
    assert not repair_transactions._allowed_rollback_command(
        ("sudo", "apt", "remove", "bash"), tool_id="git"
    )


def test_docker_special_rollback_is_exact_and_user_bound(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repair_transactions, "get_username", lambda: "alice")

    assert repair_transactions._allowed_rollback_command(
        ("sudo", "systemctl", "stop", "docker"), tool_id="docker"
    )
    assert repair_transactions._allowed_rollback_command(
        ("sudo", "gpasswd", "-d", "alice", "docker"), tool_id="docker"
    )
    assert not repair_transactions._allowed_rollback_command(
        ("sudo", "gpasswd", "-d", "bob", "docker"), tool_id="docker"
    )


def test_repair_intent_is_persisted_before_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    action = repair_transactions.RepairAction(
        tool_id="docker",
        tool_title="Docker",
        problem="service",
        risk="medium",
        command=("sudo", "systemctl", "start", "docker"),
        verification_command=None,
        rollback_command=("sudo", "systemctl", "stop", "docker"),
    )
    path = tmp_path / "transaction.json"
    payload: dict[str, object] = {
        "schema_version": 1,
        "transaction_id": "test",
        "actions": [],
    }

    def fake_run(command: list[str], check: bool) -> SimpleNamespace:
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["actions"][0]["status"] == "pending"
        assert saved["actions"][0]["rollback_command"] == [
            "sudo",
            "systemctl",
            "stop",
            "docker",
        ]
        return SimpleNamespace(returncode=1)

    monkeypatch.setattr(repair_transactions.subprocess, "run", fake_run)

    record = repair_transactions._execute_repair_action(action, payload=payload, path=path)

    assert record["status"] == "failed"
    assert json.loads(path.read_text(encoding="utf-8"))["actions"][0]["status"] == "failed"


def test_transaction_id_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="invalid transaction id"):
        repair_transactions._transaction_path("../../escape")
