from __future__ import annotations

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


def test_rollback_allowlist_accepts_generated_forms_and_blocks_arbitrary_commands() -> None:
    assert repair_transactions._allowed_rollback_command(("rpm-ostree", "uninstall", "git"))
    assert repair_transactions._allowed_rollback_command(("sudo", "dnf", "remove", "git"))
    assert repair_transactions._allowed_rollback_command(
        ("sudo", "gpasswd", "-d", "alice", "docker")
    )
    assert not repair_transactions._allowed_rollback_command(("sh", "-c", "rm -rf /"))
    assert not repair_transactions._allowed_rollback_command(("sudo", "bash", "script.sh"))


def test_transaction_id_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="invalid transaction id"):
        repair_transactions._transaction_path("../../escape")
