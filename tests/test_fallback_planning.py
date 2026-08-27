from __future__ import annotations

import pytest

from devdoctor import bootstrap, fallback_planning


def _spec(tool_id: str) -> bootstrap.ToolSpec:
    return next(spec for spec in bootstrap.get_bootstrap_tools() if spec.id == tool_id)


def _nix_system() -> dict[str, object]:
    return {"package_managers": [{"id": "nix", "installed": True}]}


def test_nix_fallback_is_limited_to_explicit_mapping() -> None:
    plan = fallback_planning.nix_plan_for_spec(_spec("git"), system=_nix_system())

    assert plan is not None
    assert plan.manager == "nix"
    assert plan.command == ("nix", "profile", "install", "nixpkgs#git")
    assert plan.rollback_command == ("nix", "profile", "remove", "nixpkgs#git")
    assert plan.requires_sudo is False


@pytest.mark.parametrize(
    ("tool_id", "package"),
    [
        ("rustc", "nixpkgs#rustup"),
        ("gh", "nixpkgs#gh"),
    ],
)
def test_nix_fallback_translates_bootstrap_ids(tool_id: str, package: str) -> None:
    plan = fallback_planning.nix_plan_for_spec(_spec(tool_id), system=_nix_system())

    assert plan is not None
    assert plan.manager == "nix"
    assert plan.package_name == package
    assert plan.command == ("nix", "profile", "install", package)


def test_nix_fallback_declines_unknown_mapping() -> None:
    spec = bootstrap.ToolSpec(
        id="custom-unmapped-tool",
        title="Custom",
        category=bootstrap.BootstrapCategory.SYSTEM,
        executable="custom",
    )

    assert fallback_planning.nix_plan_for_spec(spec, system=_nix_system()) is None
