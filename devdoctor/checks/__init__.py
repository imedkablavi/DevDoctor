"""Standard check registry for DevDoctor."""

from __future__ import annotations

from devdoctor.models import CheckCallable


def get_all_checks(*, network_timeout: float = 3.0) -> tuple[CheckCallable, ...]:
    """Return the default ordered check list."""

    from devdoctor.plugins import checks_from_plugins, get_check_plugins

    return checks_from_plugins(get_check_plugins(network_timeout=network_timeout))
