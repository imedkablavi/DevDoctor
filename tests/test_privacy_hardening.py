from __future__ import annotations

from devdoctor import hardening, privacy_hardening


def test_safe_version_token_drops_unstructured_sensitive_text() -> None:
    assert privacy_hardening.safe_version_token("token=super-secret /home/alice") is None
    assert privacy_hardening.safe_version_token("npm 10.9.3") == "10.9.3"


def test_privacy_patch_normalizes_manager_versions(monkeypatch: object) -> None:
    original = hardening.safe_diagnostic_snapshot
    previous_patched = privacy_hardening._PATCHED
    try:
        privacy_hardening._PATCHED = False
        monkeypatch.setattr(
            hardening,
            "safe_diagnostic_snapshot",
            lambda: {
                "package_managers": [
                    {"id": "npm", "version": "npm 10.9.3"},
                    {"id": "custom", "version": "token=secret /home/alice"},
                ]
            },
        )
        privacy_hardening.apply_privacy_hardening()

        snapshot = hardening.safe_diagnostic_snapshot()

        assert snapshot["package_managers"][0]["version"] == "10.9.3"
        assert snapshot["package_managers"][1]["version"] is None
        assert "secret" not in str(snapshot)
        assert "/home/alice" not in str(snapshot)
    finally:
        hardening.safe_diagnostic_snapshot = original
        privacy_hardening._PATCHED = previous_patched
