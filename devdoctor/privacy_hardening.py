"""Privacy normalization for support-oriented diagnostic output."""

from __future__ import annotations

import re
from typing import Any

from devdoctor import hardening

_PATCHED = False
_VERSION_TOKEN = re.compile(r"\d+(?:\.\d+){0,3}(?:[-+._][A-Za-z0-9.-]{1,32})?")


def safe_version_token(value: object) -> str | None:
    """Return a bounded non-identifying version token or no value."""

    if not isinstance(value, str):
        return None
    match = _VERSION_TOKEN.search(value[:256])
    if match is None:
        return None
    return match.group(0)[:64]


def apply_privacy_hardening() -> None:
    """Normalize untrusted manager-version text before diagnostics are exposed."""

    global _PATCHED
    if _PATCHED:
        return
    original = hardening.safe_diagnostic_snapshot

    def safe_diagnostic_snapshot() -> dict[str, Any]:
        payload = original()
        managers = payload.get("package_managers")
        if isinstance(managers, list):
            for manager in managers:
                if isinstance(manager, dict):
                    manager["version"] = safe_version_token(manager.get("version"))
        return payload

    hardening.safe_diagnostic_snapshot = safe_diagnostic_snapshot
    _PATCHED = True
