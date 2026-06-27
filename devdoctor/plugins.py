"""Check plugin registry and discovery support."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points

from devdoctor.checks.bun import check_bun
from devdoctor.checks.cargo import check_cargo
from devdoctor.checks.cpu import check_cpu
from devdoctor.checks.disk import check_disk
from devdoctor.checks.dns import check_dns
from devdoctor.checks.docker import check_docker
from devdoctor.checks.git import check_git
from devdoctor.checks.github import check_github_cli, check_github_reachability
from devdoctor.checks.go import check_go
from devdoctor.checks.gpu import check_gpu
from devdoctor.checks.helm import check_helm
from devdoctor.checks.internet import check_internet
from devdoctor.checks.java import check_java
from devdoctor.checks.kernel import check_kernel
from devdoctor.checks.kubectl import check_kubectl
from devdoctor.checks.node import check_node
from devdoctor.checks.npm import check_npm
from devdoctor.checks.os import check_os
from devdoctor.checks.pnpm import check_pnpm
from devdoctor.checks.podman import check_podman
from devdoctor.checks.python import check_python
from devdoctor.checks.ram import check_ram
from devdoctor.checks.rust import check_rust
from devdoctor.checks.terraform import check_terraform
from devdoctor.checks.uptime import check_uptime
from devdoctor.models import CheckCallable, CheckCategory, CheckResult

PLUGIN_ENTRY_POINT_GROUP = "devdoctor.checks"


@dataclass(frozen=True, slots=True)
class CheckPlugin:
    """Metadata and callable for a loadable check plugin."""

    id: str
    title: str
    category: CheckCategory
    section: str
    check: CheckCallable
    keywords: tuple[str, ...] = ()
    builtin: bool = True


def get_check_plugins(*, network_timeout: float = 3.0) -> tuple[CheckPlugin, ...]:
    """Return built-in and externally registered check plugins."""

    return (*_builtin_plugins(network_timeout=network_timeout), *_external_plugins())


def checks_from_plugins(plugins: Iterable[CheckPlugin]) -> tuple[CheckCallable, ...]:
    """Return check callables from plugin metadata."""

    return tuple(plugin.check for plugin in plugins)


def _builtin_plugins(*, network_timeout: float) -> tuple[CheckPlugin, ...]:
    """Return the built-in plugin list in execution order."""

    return (
        CheckPlugin("system.os", "Linux Distribution", CheckCategory.SYSTEM, "System", check_os),
        CheckPlugin("system.kernel", "Kernel", CheckCategory.SYSTEM, "System", check_kernel),
        CheckPlugin("system.cpu", "CPU", CheckCategory.SYSTEM, "System", check_cpu),
        CheckPlugin("system.ram", "RAM", CheckCategory.SYSTEM, "System", check_ram),
        CheckPlugin("system.disk", "Disk Space", CheckCategory.SYSTEM, "System", check_disk),
        CheckPlugin("system.uptime", "Uptime", CheckCategory.SYSTEM, "System", check_uptime),
        CheckPlugin("system.gpu", "GPU", CheckCategory.SYSTEM, "System", check_gpu),
        CheckPlugin("tool.git", "Git", CheckCategory.TOOL, "Development Tools", check_git),
        CheckPlugin("tool.python", "Python", CheckCategory.TOOL, "Development Tools", check_python),
        CheckPlugin("tool.docker", "Docker", CheckCategory.TOOL, "Containers", check_docker),
        CheckPlugin("tool.podman", "Podman", CheckCategory.TOOL, "Containers", check_podman),
        CheckPlugin("tool.node", "Node.js", CheckCategory.TOOL, "Development Tools", check_node),
        CheckPlugin("tool.npm", "npm", CheckCategory.TOOL, "Development Tools", check_npm),
        CheckPlugin("tool.pnpm", "pnpm", CheckCategory.TOOL, "Development Tools", check_pnpm),
        CheckPlugin("tool.bun", "Bun", CheckCategory.TOOL, "Development Tools", check_bun),
        CheckPlugin("tool.rust", "Rust", CheckCategory.TOOL, "Development Tools", check_rust),
        CheckPlugin("tool.cargo", "Cargo", CheckCategory.TOOL, "Development Tools", check_cargo),
        CheckPlugin("tool.go", "Go", CheckCategory.TOOL, "Development Tools", check_go),
        CheckPlugin("tool.java", "Java", CheckCategory.TOOL, "Development Tools", check_java),
        CheckPlugin(
            "tool.github_cli",
            "GitHub CLI",
            CheckCategory.TOOL,
            "Development Tools",
            check_github_cli,
            keywords=("gh",),
        ),
        CheckPlugin(
            "tool.kubectl", "kubectl", CheckCategory.TOOL, "Development Tools", check_kubectl
        ),
        CheckPlugin("tool.helm", "Helm", CheckCategory.TOOL, "Development Tools", check_helm),
        CheckPlugin(
            "tool.terraform",
            "Terraform",
            CheckCategory.TOOL,
            "Development Tools",
            check_terraform,
        ),
        CheckPlugin(
            "network.internet",
            "Internet Connectivity",
            CheckCategory.NETWORK,
            "Networking",
            _bind_timeout(check_internet, timeout=network_timeout, name="check_internet"),
            keywords=("internet", "connectivity", "latency"),
        ),
        CheckPlugin(
            "network.dns",
            "DNS Resolution",
            CheckCategory.NETWORK,
            "Networking",
            _bind_timeout(check_dns, timeout=network_timeout, name="check_dns"),
            keywords=("dns", "resolver"),
        ),
        CheckPlugin(
            "network.github",
            "GitHub Reachability",
            CheckCategory.NETWORK,
            "Networking",
            _bind_timeout(
                check_github_reachability,
                timeout=network_timeout,
                name="check_github_reachability",
            ),
            keywords=("github", "https"),
        ),
    )


def _bind_timeout(
    check: Callable[[float], CheckResult],
    *,
    timeout: float,
    name: str,
) -> CheckCallable:
    """Bind a timeout argument while preserving a helpful check name."""

    def wrapped() -> CheckResult:
        return check(timeout)

    wrapped.__name__ = name
    return wrapped


def _external_plugins() -> tuple[CheckPlugin, ...]:
    """Load optional third-party plugins from entry points."""

    discovered: list[CheckPlugin] = []
    for entry_point in _plugin_entry_points():
        plugin = _load_entry_point(entry_point)
        if plugin is not None:
            discovered.append(plugin)
    return tuple(discovered)


def _plugin_entry_points() -> tuple[EntryPoint, ...]:
    """Return registered plugin entry points across supported metadata APIs."""

    all_entry_points = entry_points()
    if hasattr(all_entry_points, "select"):
        return tuple(all_entry_points.select(group=PLUGIN_ENTRY_POINT_GROUP))
    return tuple(all_entry_points.get(PLUGIN_ENTRY_POINT_GROUP, ()))  # type: ignore[union-attr]


def _load_entry_point(entry_point: EntryPoint) -> CheckPlugin | None:
    """Load one external plugin entry point safely."""

    try:
        loaded = entry_point.load()
    except Exception:
        return None

    if isinstance(loaded, CheckPlugin):
        return loaded
    if callable(loaded):
        title = entry_point.name.replace("_", " ").title()
        return CheckPlugin(
            id=f"external.{entry_point.name}",
            title=title,
            category=CheckCategory.SYSTEM,
            section="Plugins",
            check=loaded,
            keywords=(entry_point.name,),
            builtin=False,
        )
    return None
