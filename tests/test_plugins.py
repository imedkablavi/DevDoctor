from __future__ import annotations

from devdoctor.models import CheckCategory
from devdoctor.plugins import checks_from_plugins, get_check_plugins


def test_builtin_plugins_preserve_check_order_and_metadata() -> None:
    plugins = get_check_plugins(network_timeout=0.5)

    assert plugins[0].id == "system.os"
    assert plugins[0].category is CheckCategory.SYSTEM
    assert any(plugin.id == "tool.docker" and plugin.section == "Containers" for plugin in plugins)
    assert len(checks_from_plugins(plugins)) == len(plugins)
