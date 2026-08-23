from __future__ import annotations

from devdoctor import bootstrap


def test_mutating_system_manager_plans_have_rollback_commands() -> None:
    for manager in ("apt", "dnf", "rpm-ostree", "pacman", "zypper"):
        command, _dry_run, rollback = bootstrap._manager_commands(manager, "example")

        assert command is not None
        assert rollback is not None, manager


def test_supported_simulation_managers_have_non_mutating_preview_commands() -> None:
    for manager in ("apt", "dnf", "pacman", "zypper", "flatpak"):
        command, dry_run, _rollback = bootstrap._manager_commands(manager, "example")

        assert command is not None
        assert dry_run is not None, manager
        assert dry_run != command


def test_transactional_managers_without_simulation_are_explicitly_skippable() -> None:
    for manager in ("rpm-ostree", "nix", "brew"):
        command, dry_run, _rollback = bootstrap._manager_commands(manager, "example")

        assert command is not None
        assert dry_run is None


def test_all_system_mutations_remain_explicit_commands() -> None:
    for manager in ("apt", "dnf", "rpm-ostree", "pacman", "zypper"):
        command, _dry_run, _rollback = bootstrap._manager_commands(manager, "example")

        assert command is not None
        assert command[0] in {"sudo", "rpm-ostree"}
