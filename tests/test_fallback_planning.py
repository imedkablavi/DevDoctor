from __future__ import annotations

from devdoctor import bootstrap, fallback_planning


def _git_spec() -> bootstrap.ToolSpec:
    return next(spec for spec in bootstrap.get_bootstrap_tools() if spec.id == "git")


def test_nix_fallback_is_limited_to_explicit_mapping() -> None:
    system = {
        "package_managers": [
            {"id": "nix", "installed": True},
        ],
    }

    plan = fallback_planning.nix_plan_for_spec(_git_spec(), system=system)

    assert plan is not None
    assert plan.manager == "nix"
    assert plan.command == ("nix", "profile", "install", "nixpkgs#git")
    assert plan.rollback_command == ("nix", "profile", "remove", "nixpkgs#git")
    assert plan.requires_sudo is False


def test_nix_fallback_declines_unknown_mapping() -> None:
    spec = bootstrap.ToolSpec(
        id="custom-unmapped-tool",
        title="Custom",
        category=bootstrap.BootstrapCategory.SYSTEM,
        executable="custom",
    )
    system = {"package_managers": [{"id": "nix", "installed": True}]}

    assert fallback_planning.nix_plan_for_spec(spec, system=system) is None
