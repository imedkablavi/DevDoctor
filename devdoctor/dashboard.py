"""Interactive Textual dashboard for DevDoctor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from rich.console import Group
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    Static,
)
from textual.worker import Worker, WorkerState

from devdoctor.actions import MaintenanceAction, auto_fix_plans, optimizer_actions
from devdoctor.clipboard import copy_to_clipboard
from devdoctor.doctor import DevDoctor
from devdoctor.exporters.html import write_html_report
from devdoctor.exporters.json import write_json_report
from devdoctor.exporters.markdown import render_markdown, write_markdown_report
from devdoctor.exporters.pdf import write_pdf_report
from devdoctor.models import CheckCategory, CheckResult, HealthReport
from devdoctor.package_managers import InstallPlan, detect_package_managers, install_plan_for_tool
from devdoctor.paths import latest_report_path, state_dir
from devdoctor.ui.theme import status_icon


@dataclass(frozen=True, slots=True)
class NavItem:
    """Sidebar navigation item."""

    id: str
    title: str
    subtitle: str
    keywords: tuple[str, ...] = ()


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem(
        "overview",
        "Health Overview",
        "Score, scan status, recommendations",
        ("health", "score"),
    ),
    NavItem("system", "System", "CPU, RAM, GPU, disk, kernel", ("cpu", "ram", "gpu", "disk")),
    NavItem("tools", "Development Tools", "Languages and CLIs", ("git", "python", "node", "rust")),
    NavItem("containers", "Containers", "Docker and Podman", ("docker", "podman")),
    NavItem("networking", "Networking", "Internet, DNS, GitHub", ("dns", "github", "latency")),
    NavItem("security", "Security", "Local posture checks", ("security", "permissions")),
    NavItem("packages", "Packages", "Package managers", ("apt", "dnf", "pacman", "flatpak")),
    NavItem("optimization", "Optimization", "Cleanup actions", ("clean", "cache", "journal")),
    NavItem("autofix", "Auto Fix", "Missing tools and repair plans", ("fix", "install", "missing")),
    NavItem(
        "reports",
        "Reports",
        "JSON, HTML, Markdown, PDF, clipboard",
        ("export", "json", "pdf"),
    ),
    NavItem("shortcuts", "Shortcuts", "Keyboard map and workflow keys", ("keyboard", "help")),
    NavItem("settings", "Settings", "Theme and refresh preferences", ("theme", "interval")),
    NavItem("about", "About", "Project information", ("version", "help")),
    NavItem("quit", "Quit", "Close DevDoctor", ("exit", "q")),
)

TOOL_DESCRIPTIONS = {
    "tool.git": ("Distributed version control system.", "https://git-scm.com/"),
    "tool.docker": ("Container runtime and image tooling.", "https://docs.docker.com/engine/"),
    "tool.podman": ("Daemonless container engine.", "https://podman.io/"),
    "tool.python": ("Python runtime used by DevDoctor and Python projects.", "https://python.org/"),
    "tool.node": ("JavaScript runtime for frontend and backend tooling.", "https://nodejs.org/"),
    "tool.npm": ("Node.js package manager.", "https://www.npmjs.com/"),
    "tool.pnpm": ("Fast disk-efficient JavaScript package manager.", "https://pnpm.io/"),
    "tool.bun": ("JavaScript runtime, package manager, and bundler.", "https://bun.sh/"),
    "tool.rust": ("Rust compiler.", "https://www.rust-lang.org/tools/install"),
    "tool.cargo": ("Rust package manager and build tool.", "https://doc.rust-lang.org/cargo/"),
    "tool.go": ("Go compiler and toolchain.", "https://go.dev/"),
    "tool.java": ("Java runtime and development kit.", "https://openjdk.org/"),
    "tool.github_cli": ("GitHub command-line interface.", "https://cli.github.com/"),
    "tool.kubectl": (
        "Kubernetes command-line interface.",
        "https://kubernetes.io/docs/tasks/tools/",
    ),
    "tool.helm": ("Kubernetes package manager.", "https://helm.sh/"),
    "tool.terraform": ("Infrastructure as code CLI.", "https://developer.hashicorp.com/terraform"),
}

NAV_ICONS = {
    "overview": "◆",
    "system": "◈",
    "tools": "▣",
    "containers": "▤",
    "networking": "⌁",
    "security": "◇",
    "packages": "▦",
    "optimization": "↯",
    "autofix": "✦",
    "reports": "⇩",
    "shortcuts": "⌘",
    "settings": "⚙",
    "about": "?",
    "quit": "x",
}


class CommandModal(ModalScreen[None]):
    """Confirmation dialog for commands that must not run automatically."""

    CSS = """
    CommandModal {
        align: center middle;
    }

    #command-dialog {
        width: min(86, 90%);
        height: auto;
        border: heavy $accent;
        background: $surface;
        padding: 1 2;
    }

    #command-dialog Static {
        margin-bottom: 1;
    }

    #command-buttons {
        height: auto;
        align-horizontal: right;
    }
    """

    def __init__(self, title: str, command: str, note: str) -> None:
        super().__init__()
        self.dialog_title = title
        self.command = command
        self.note = note

    def compose(self) -> ComposeResult:
        with Vertical(id="command-dialog"):
            yield Label(self.dialog_title, classes="dialog-title")
            yield Static(self.note)
            yield Static(f"$ {self.command}", classes="command-preview")
            with Horizontal(id="command-buttons"):
                yield Button("Copy Command", id="copy-command", variant="primary")
                yield Button("Close", id="close-command")

    @on(Button.Pressed, "#copy-command")
    def copy_command(self) -> None:
        result = copy_to_clipboard(self.command)
        self.app.notify(result.message, severity="information" if result.copied else "warning")

    @on(Button.Pressed, "#close-command")
    def close_dialog(self) -> None:
        self.dismiss()


class ToolDetailModal(ModalScreen[None]):
    """Detailed page for one tool check."""

    CSS = """
    ToolDetailModal {
        align: center middle;
    }

    #tool-detail {
        width: min(96, 92%);
        max-height: 90%;
        border: heavy $accent;
        background: $surface;
        padding: 1 2;
    }

    #tool-detail .detail-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, result: CheckResult) -> None:
        super().__init__()
        self.result = result

    def compose(self) -> ComposeResult:
        description, website = TOOL_DESCRIPTIONS.get(
            self.result.id,
            ("Developer tool or environment dependency.", "Not available"),
        )
        plan = install_plan_for_tool(self.result.id, self.result.title)
        status = f"{status_icon(self.result.status)} {self.result.status.value.upper()}"
        version = self.result.details.get("version") or self.result.details.get("python_version")
        path = self.result.details.get("path") or self.result.details.get("python_executable")

        with VerticalScroll(id="tool-detail"):
            yield Label(self.result.title, classes="detail-title")
            yield Static(f"Status: {status}")
            yield Static(f"Version: {version or 'Not detected'}")
            yield Static(f"Install location: {path or 'Not detected'}")
            yield Static(f"Description: {description}")
            yield Static(f"Official website: {website}")
            yield Static(f"Current recommendation: {self.result.recommendation or 'None'}")
            if plan:
                yield Static(f"Installation method: {plan.manager}")
                yield Static(f"Package command: {plan.command}", classes="command-preview")
                yield Button("Install", id="install-tool", variant="warning")
            yield Button("Close", id="close-detail")

    @on(Button.Pressed, "#install-tool")
    def confirm_install(self) -> None:
        plan = install_plan_for_tool(self.result.id, self.result.title)
        if plan is None:
            self.app.notify("No install plan is available for this tool.", severity="warning")
            return
        self.app.push_screen(
            CommandModal(
                title=f"Install {self.result.title}",
                command=plan.command,
                note=f"{plan.note}\n\nDevDoctor will not run this command automatically.",
            )
        )

    @on(Button.Pressed, "#close-detail")
    def close_detail(self) -> None:
        self.dismiss()


class DevDoctorDashboard(App[None]):
    """Textual dashboard application."""

    TITLE = "DevDoctor"
    SUB_TITLE = "Diagnose your development environment in seconds."
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("/", "focus_search", "Search", show=True, priority=True),
        Binding("tab", "next_page", "Next Page", show=True, priority=True),
        Binding("ctrl+r", "refresh", "Refresh", show=True, priority=True),
        Binding("ctrl+e", "show_reports", "Export", show=True, priority=True),
        Binding("ctrl+f", "show_autofix", "Auto Fix", show=True, priority=True),
        Binding("escape", "back", "Back", show=True, priority=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    CSS = """
    Screen {
        background: #0b1020;
        color: #dbe7f3;
    }

    Screen.light-mode {
        background: #f8fafc;
        color: #0f172a;
    }

    #shell {
        height: 1fr;
    }

    #sidebar {
        width: 28;
        min-width: 22;
        border-right: solid #243247;
        background: #0f1726;
        padding: 1;
    }

    Screen.light-mode #sidebar {
        border-right: solid #cbd5e1;
        background: #eaf2f8;
    }

    #brand {
        text-style: bold;
        color: #7dd3fc;
        margin-bottom: 1;
    }

    Screen.light-mode #brand {
        color: #0369a1;
    }

    #brand-subtitle {
        color: #94a3b8;
        margin-bottom: 1;
    }

    Screen.light-mode #brand-subtitle,
    Screen.light-mode .muted {
        color: #475569;
    }

    #search {
        margin-bottom: 1;
    }

    #nav {
        height: 1fr;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem.--highlight {
        background: #1e3a5f;
        color: white;
    }

    Screen.light-mode ListItem.--highlight {
        background: #bae6fd;
        color: #0f172a;
    }

    #content {
        width: 1fr;
        padding: 1;
    }

    .loading-shell {
        align: center middle;
        min-height: 16;
    }

    .page-title {
        text-style: bold;
        color: #e5edf7;
        margin-bottom: 1;
    }

    Screen.light-mode .page-title {
        color: #0f172a;
    }

    .muted {
        color: #94a3b8;
    }

    .card {
        border: solid #2f3f56;
        background: #111827;
        padding: 1 2;
        margin: 0 1 1 0;
        min-height: 7;
    }

    Screen.light-mode .card {
        border: solid #cbd5e1;
        background: #ffffff;
        color: #0f172a;
    }

    .health-card {
        border: heavy #22d3ee;
        background: #0f1c2f;
        padding: 1 2;
        margin-bottom: 1;
    }

    Screen.light-mode .health-card {
        border: heavy #0284c7;
        background: #eef9ff;
        color: #0f172a;
    }

    .score-hero {
        text-style: bold;
        color: #67e8f9;
    }

    .metric-card {
        min-height: 5;
    }

    .tool-card {
        min-width: 36;
        height: 10;
    }

    .status-pass {
        color: #34d399;
    }

    .status-warning {
        color: #fbbf24;
    }

    .status-fail {
        color: #fb7185;
    }

    .command-preview {
        background: #060914;
        color: #cffafe;
        padding: 1;
    }

    Screen.light-mode .command-preview {
        background: #e2e8f0;
        color: #0f172a;
    }

    Button {
        margin-right: 1;
        min-width: 14;
    }
    """

    def __init__(self, *, network_timeout: float = 3.0, refresh_interval: int = 300) -> None:
        super().__init__()
        self.network_timeout = network_timeout
        self.refresh_interval = refresh_interval
        self.report: HealthReport | None = None
        self.selected_page = "overview"
        self.page_history: list[str] = []
        self.last_scan_label = "Not scanned yet"
        self.scanning = False
        self.current_theme_label = "Dark"
        self.refresh_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="shell"):
            with Vertical(id="sidebar"):
                yield Static("◆ DevDoctor", id="brand")
                yield Static("workstation health", id="brand-subtitle")
                yield Input(placeholder="Search: docker, dns, python", id="search")
                with ListView(id="nav"):
                    for item in NAV_ITEMS:
                        yield ListItem(Label(_nav_label(item)), id=f"nav-{item.id}")
            with VerticalScroll(id="content"):
                yield Static("Loading dashboard...", classes="muted")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#nav", ListView).index = 0
        self.run_scan()
        self.refresh_timer = self.set_interval(self.refresh_interval, self.run_scan)

    @on(ListView.Selected, "#nav")
    async def navigate(self, event: ListView.Selected) -> None:
        page_id = (event.item.id or "nav-overview").removeprefix("nav-")
        if page_id == "quit":
            self.exit()
            return
        await self.set_page(page_id)

    @on(Input.Changed, "#search")
    async def search_changed(self, event: Input.Changed) -> None:
        query = event.value.strip().lower()
        if not query:
            return
        target = self.find_search_target(query)
        if target is None:
            return
        if target.startswith("tool:"):
            result = self.result_by_id(target.removeprefix("tool:"))
            if result is not None:
                self.push_screen(ToolDetailModal(result))
            return
        await self.set_page(target)

    @on(Button.Pressed, ".tool-open")
    def open_tool_card(self, event: Button.Pressed) -> None:
        if event.button.id is None:
            return
        result = self.result_by_id(_unsafe_id(event.button.id.removeprefix("tool-open-")))
        if result is not None:
            self.push_screen(ToolDetailModal(result))

    @on(Button.Pressed, ".command-action")
    def open_command_action(self, event: Button.Pressed) -> None:
        if event.button.id is None:
            return
        action = self.action_by_button_id(event.button.id)
        if action is None:
            return
        self.push_screen(
            CommandModal(
                title=action.title,
                command=action.command,
                note=(
                    f"{action.description}\nEstimated freed space: {action.estimated_freed}\n\n"
                    "DevDoctor requires confirmation and will not run this command automatically."
                ),
            )
        )

    @on(Button.Pressed, ".install-action")
    def open_install_action(self, event: Button.Pressed) -> None:
        if event.button.id is None or self.report is None:
            return
        plan = self.install_plan_by_button_id(event.button.id)
        if plan is None:
            return
        self.push_screen(
            CommandModal(
                title=f"Install {plan.tool_title}",
                command=plan.command,
                note=f"{plan.note}\n\nDevDoctor will not run this command automatically.",
            )
        )

    @on(Button.Pressed, ".report-action")
    def run_report_action(self, event: Button.Pressed) -> None:
        if self.report is None:
            self.notify("Run a scan before exporting reports.", severity="warning")
            return
        report_dir = state_dir()
        report_dir.mkdir(parents=True, exist_ok=True)
        if event.button.id == "report-json":
            path = write_json_report(self.report, report_dir / "devdoctor-report.json")
        elif event.button.id == "report-html":
            path = write_html_report(self.report, report_dir / "devdoctor-report.html")
        elif event.button.id == "report-md":
            path = write_markdown_report(self.report, report_dir / "devdoctor-report.md")
        elif event.button.id == "report-pdf":
            path = write_pdf_report(self.report, report_dir / "devdoctor-report.pdf")
        elif event.button.id == "report-copy":
            result = copy_to_clipboard(render_markdown(self.report))
            self.notify(result.message, severity="information" if result.copied else "warning")
            return
        else:
            return
        self.notify(f"Report written: {path}", severity="information")

    @on(Button.Pressed, ".settings-action")
    def apply_setting(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "setting-dark":
                self.current_theme_label = "Dark"
                self.theme = "textual-dark"
                self.set_class(False, "light-mode")
                self.notify("Dark theme selected.")
            case "setting-light":
                self.current_theme_label = "Light"
                self.theme = "textual-light"
                self.set_class(True, "light-mode")
                self.notify("Light theme selected.")
            case "setting-refresh-60":
                self.set_refresh_interval(60)
            case "setting-refresh-300":
                self.set_refresh_interval(300)
        self.refresh_current_page()

    @on(Worker.StateChanged)
    def scan_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name != "scan":
            return
        if event.state is WorkerState.RUNNING:
            self.scanning = True
            self.last_scan_label = "Scanning..."
            self.call_later(self.refresh_current_page)
        elif event.state is WorkerState.SUCCESS:
            self.scanning = False
            self.report = event.worker.result
            self.last_scan_label = datetime.now().strftime("%H:%M:%S")
            if self.report is not None:
                write_json_report(self.report, latest_report_path())
            self.call_later(self.refresh_current_page)
        elif event.state in {WorkerState.ERROR, WorkerState.CANCELLED}:
            self.scanning = False
            self.last_scan_label = "Scan failed"
            self.notify("Scan failed. Existing report is still available.", severity="error")
            self.call_later(self.refresh_current_page)

    def run_scan(self) -> None:
        """Run checks in a background worker."""

        if self.scanning:
            return
        doctor = DevDoctor.default(network_timeout=self.network_timeout)
        self.run_worker(
            doctor.run,
            name="scan",
            group="scan",
            exclusive=True,
            thread=True,
            exit_on_error=False,
        )

    def set_refresh_interval(self, seconds: int) -> None:
        """Update background refresh cadence."""

        self.refresh_interval = seconds
        if self.refresh_timer is not None:
            self.refresh_timer.stop()
        self.refresh_timer = self.set_interval(self.refresh_interval, self.run_scan)
        self.notify(f"Refresh interval set to {seconds} seconds.")

    async def set_page(self, page_id: str) -> None:
        """Select and render a dashboard page."""

        if page_id != self.selected_page:
            self.page_history.append(self.selected_page)
        self.selected_page = page_id
        self.sync_sidebar_selection()
        await self.render_current_page()

    def refresh_current_page(self) -> None:
        """Schedule rendering for the selected page."""

        self.run_worker(self.render_current_page, name="render", group="render", exclusive=True)

    async def render_current_page(self) -> None:
        """Replace the main content with the selected page."""

        content = self.query_one("#content", VerticalScroll)
        await content.remove_children()
        widgets = self.page_widgets(self.selected_page)
        await content.mount(*widgets)

    def page_widgets(self, page_id: str) -> tuple[object, ...]:
        """Build widgets for one page."""

        if self.report is None:
            return (
                Static("◆ DevDoctor", classes="page-title"),
                Vertical(
                    LoadingIndicator(),
                    Static("Scanning your workstation...", classes="muted"),
                    Static("Checks run in the background and never require root.", classes="muted"),
                    classes="loading-shell card",
                ),
            )
        match page_id:
            case "overview":
                return self.overview_page()
            case "system":
                return self.system_page()
            case "tools":
                tool_results = tuple(
                    result
                    for result in self.report.results
                    if result.category is CheckCategory.TOOL
                )
                return self.tools_page(tool_results)
            case "containers":
                return self.tools_page(
                    tuple(
                        result
                        for result in self.report.results
                        if result.id in {"tool.docker", "tool.podman"}
                    ),
                    title="Containers",
                )
            case "networking":
                return self.networking_page()
            case "security":
                return self.security_page()
            case "packages":
                return self.packages_page()
            case "optimization":
                return self.optimization_page()
            case "autofix":
                return self.autofix_page()
            case "reports":
                return self.reports_page()
            case "shortcuts":
                return self.shortcuts_page()
            case "settings":
                return self.settings_page()
            case "about":
                return self.about_page()
            case _:
                return self.overview_page()

    def overview_page(self) -> tuple[object, ...]:
        report = self.require_report()
        summary = report.summary
        progress = ProgressBar(total=100, completed=report.score, width=60)
        health = Static(
            Panel(
                Group(
                    Text(f"{report.score}/100", style="bold bright_cyan"),
                    Text("Overall workstation health", style="bright_black"),
                    progress,
                    Text(
                        f"✓ {summary.passed} passed   "
                        f"⚠ {summary.warnings} warnings   "
                        f"✕ {summary.failed} failed"
                    ),
                    Text(f"Last Scan: {self.last_scan_label}", style="bright_black"),
                ),
                title="Health Overview",
                border_style="cyan",
            ),
            classes="health-card",
        )
        recommendations = Table.grid(expand=True)
        recommendations.add_column(ratio=1)
        if report.recommendations:
            for index, recommendation in enumerate(report.recommendations, start=1):
                recommendations.add_row(f"{index}. {recommendation}")
        else:
            recommendations.add_row(
                "No recommendations. Your development environment looks healthy."
            )
        return (
            Static("Health Overview", classes="page-title"),
            health,
            self.overview_health_cards(),
            Static(
                Panel(recommendations, title="Recommendations", border_style="yellow"),
                classes="card",
            ),
        )

    def system_page(self) -> tuple[object, ...]:
        info = self.require_report().system_info
        cards = (
            (
                "CPU",
                "\n".join(
                    (
                        str(info.get("cpu", "Not available")),
                        f"Usage: {_display_percent(info.get('cpu_usage_percent'))}",
                        f"Cores: {info.get('physical_cores', 'unknown')} physical / "
                        f"{info.get('logical_cores', 'unknown')} logical",
                        "Load: "
                        f"{info.get('load_1m', 'n/a')} / "
                        f"{info.get('load_5m', 'n/a')} / "
                        f"{info.get('load_15m', 'n/a')}",
                    )
                ),
            ),
            (
                "Memory",
                "\n".join(
                    (
                        f"RAM: {info.get('ram_total', 'unknown')}",
                        f"Available: {info.get('ram_available', 'unknown')}",
                        f"Used: {_display_percent(info.get('ram_used_percent'))}",
                        f"Swap: {info.get('swap_total', 'unknown')} "
                        f"({_display_percent(info.get('swap_used_percent'))})",
                    )
                ),
            ),
            (
                "Disk",
                "\n".join(
                    (
                        f"Path: {info.get('disk_path', 'unknown')}",
                        f"Free: {info.get('disk_free', 'unknown')}",
                        f"Used: {_display_percent(info.get('disk_used_percent'))}",
                        f"Filesystem: {info.get('filesystem', 'unknown')}",
                        f"Device: {info.get('disk_device', 'unknown')}",
                    )
                ),
            ),
            (
                "Session",
                "\n".join(
                    (
                        f"Desktop: {info.get('desktop_environment', 'unknown')}",
                        f"Session: {info.get('session_type', 'unknown')}",
                        f"Shell: {info.get('shell', 'unknown')}",
                        f"Terminal: {info.get('terminal', 'unknown')}",
                        f"Package manager: {info.get('primary_package_manager', 'unknown')}",
                    )
                ),
            ),
            (
                "Platform",
                "\n".join(
                    (
                        str(info.get("distribution", "unknown")),
                        f"Kernel: {info.get('kernel', 'unknown')}",
                        f"Arch: {info.get('architecture', 'unknown')}",
                        f"Hostname: {info.get('hostname', 'unknown')}",
                        f"Uptime: {info.get('uptime', 'unknown')}",
                    )
                ),
            ),
            (
                "Hardware",
                "\n".join(
                    (
                        f"GPU: {info.get('gpu', 'Not detected')}",
                        f"Battery: {info.get('battery', 'Not detected')}",
                        f"Temperature: {info.get('temperature', 'Not detected')}",
                    )
                ),
            ),
        )
        card_widgets = [
            Static(self.metric_panel(title, value), classes="card metric-card")
            for title, value in cards
        ]
        cards = self.card_grid(card_widgets)
        return (Static("System", classes="page-title"), cards)

    def tools_page(
        self,
        results: tuple[CheckResult, ...],
        *,
        title: str = "Development Tools",
    ) -> tuple[object, ...]:
        cards: list[Vertical] = []
        for result in results:
            version = (
                result.details.get("version")
                or result.details.get("python_version")
                or "Not detected"
            )
            path = (
                result.details.get("path")
                or result.details.get("python_executable")
                or "Not detected"
            )
            body = (
                f"{status_icon(result.status)} {result.status.value.upper()}\n"
                f"Version: {version}\n"
                f"Path: {path}\n"
                f"{result.recommendation or result.summary}"
            )
            cards.append(
                Vertical(
                    Static(body),
                    Button(
                        "Open Details",
                        id=f"tool-open-{_safe_id(result.id)}",
                        classes="tool-open",
                        variant="primary",
                    ),
                    classes="card tool-card",
                )
            )
        grid = self.card_grid(cards)
        return (Static(title, classes="page-title"), grid)

    def networking_page(self) -> tuple[object, ...]:
        cards: list[Static] = []
        for result in (
            self.result_by_id("network.internet"),
            self.result_by_id("network.dns"),
            self.result_by_id("network.github"),
        ):
            if result is None:
                continue
            details = self.network_detail_lines(result)
            cards.append(
                Static(
                    self.metric_panel(
                        result.title,
                        "\n".join(
                            (
                                f"{status_icon(result.status)} {result.summary}",
                                *details,
                                result.recommendation or "No action required.",
                            )
                        ),
                    ),
                    classes="card metric-card",
                )
            )
        return (
            Static("Networking", classes="page-title"),
            self.card_grid(cards),
        )

    def security_page(self) -> tuple[object, ...]:
        report = self.require_report()
        docker = self.result_by_id("tool.docker")
        github = self.result_by_id("tool.github_cli")
        signals = (
            (
                "Rootless containers",
                self._status_label(self.result_by_id("tool.podman")),
                "Prefer rootless Podman or locked-down Docker access.",
            ),
            (
                "Docker socket",
                self._status_label(docker),
                "Keep Docker socket access limited to trusted users.",
            ),
            (
                "GitHub CLI",
                self._status_label(github),
                "Use `gh auth status` for authenticated GitHub workflows.",
            ),
            (
                "Network reachability",
                self._status_label(self.result_by_id("network.github")),
                "GitHub access supports common source and dependency workflows.",
            ),
        )
        cards = [
            Static(self.metric_panel(title, f"{status}\n{guidance}"), classes="card metric-card")
            for title, status, guidance in signals
        ]
        return (
            Static("Security", classes="page-title"),
            self.card_grid(cards),
            Static(f"Current score: {report.score}/100", classes="muted"),
        )

    def packages_page(self) -> tuple[object, ...]:
        cards: list[Static] = []
        for manager in detect_package_managers():
            status = "✓ Installed" if manager.installed else "○ Not detected"
            cards.append(
                Static(
                    self.metric_panel(
                        manager.title,
                        "\n".join(
                            (
                                status,
                                f"Version: {manager.version or 'Not detected'}",
                                f"Path: {manager.path or 'No executable found'}",
                                f"Family: {manager.family}",
                                f"Command: {manager.command_hint}",
                            )
                        ),
                    ),
                    classes="card metric-card",
                )
            )
        return (Static("Packages", classes="page-title"), self.card_grid(cards))

    def optimization_page(self) -> tuple[object, ...]:
        rows: list[object] = [Static("Optimization", classes="page-title")]
        for action in optimizer_actions():
            rows.append(
                Vertical(
                    Static(
                        f"{action.title}\n{action.description}\n"
                        f"Estimated freed space: {action.estimated_freed}\n"
                        f"Risk: {_action_risk(action)}\n{action.command}"
                    ),
                    Button(
                        "Review Command",
                        id=f"action-{_safe_id(action.id)}",
                        classes="command-action",
                    ),
                    classes="card",
                )
            )
        return tuple(rows)

    def autofix_page(self) -> tuple[object, ...]:
        report = self.require_report()
        plans = auto_fix_plans(report.results)
        rows: list[object] = [Static("Auto Fix", classes="page-title")]
        if not plans:
            rows.append(Static("No installable missing-tool fixes detected.", classes="card"))
            return tuple(rows)
        for category, category_plans in _group_install_plans(plans).items():
            rows.append(Static(category, classes="page-title"))
            for plan in category_plans:
                rows.append(
                    Vertical(
                        Static(
                            "\n".join(
                                (
                                    plan.tool_title,
                                    f"Reason: {plan.note}",
                                    f"Estimated time: {_plan_estimated_time(plan)}",
                                    f"Risk: {_plan_risk(plan)}",
                                    plan.command,
                                )
                            )
                        ),
                        Button(
                            "Review Install",
                            id=f"install-{_safe_id(plan.tool_id)}",
                            classes="install-action",
                        ),
                        classes="card",
                    )
                )
        return tuple(rows)

    def reports_page(self) -> tuple[object, ...]:
        report_dir = state_dir()
        cards = [
            Vertical(
                Static(f"JSON\nMachine-readable report.\n{report_dir / 'devdoctor-report.json'}"),
                Button("Export JSON", id="report-json", classes="report-action", variant="primary"),
                classes="card metric-card",
            ),
            Vertical(
                Static(f"HTML\nStandalone visual report.\n{report_dir / 'devdoctor-report.html'}"),
                Button("Export HTML", id="report-html", classes="report-action"),
                classes="card metric-card",
            ),
            Vertical(
                Static(
                    f"Markdown\nIssue and handoff format.\n{report_dir / 'devdoctor-report.md'}"
                ),
                Button("Export Markdown", id="report-md", classes="report-action"),
                classes="card metric-card",
            ),
            Vertical(
                Static(f"PDF\nCompact shareable summary.\n{report_dir / 'devdoctor-report.pdf'}"),
                Button("Export PDF", id="report-pdf", classes="report-action"),
                classes="card metric-card",
            ),
            Vertical(
                Static("Clipboard\nCopy a Markdown report for issues or chat."),
                Button("Copy Report", id="report-copy", classes="report-action"),
                classes="card metric-card",
            ),
        ]
        return (
            Static("Reports", classes="page-title"),
            Static("Exports are written to the DevDoctor user state directory.", classes="muted"),
            self.card_grid(cards),
        )

    def shortcuts_page(self) -> tuple[object, ...]:
        shortcuts = (
            ("/", "Search", "Focus global search. Exact tool names open details immediately."),
            ("Tab", "Next Page", "Move through dashboard pages without leaving the keyboard."),
            ("Ctrl+R", "Refresh", "Run checks again in the background."),
            ("Ctrl+E", "Reports", "Open report export actions."),
            ("Ctrl+F", "Auto Fix", "Open install-plan recommendations."),
            ("Esc", "Back", "Return to the previous dashboard page."),
            ("Q", "Quit", "Close DevDoctor."),
        )
        cards = [
            Static(self.metric_panel(key, f"{title}\n{detail}"), classes="card metric-card")
            for key, title, detail in shortcuts
        ]
        return (Static("Shortcuts", classes="page-title"), self.card_grid(cards))

    def settings_page(self) -> tuple[object, ...]:
        cards = [
            Vertical(
                Static(f"Theme\nCurrently {self.current_theme_label}."),
                Horizontal(
                    Button("Dark", id="setting-dark", classes="settings-action", variant="primary"),
                    Button("Light", id="setting-light", classes="settings-action"),
                ),
                classes="card metric-card",
            ),
            Vertical(
                Static(f"Refresh interval\nCurrently {self.refresh_interval}s."),
                Horizontal(
                    Button("60s", id="setting-refresh-60", classes="settings-action"),
                    Button("300s", id="setting-refresh-300", classes="settings-action"),
                ),
                classes="card metric-card",
            ),
            Static(
                self.metric_panel(
                    "Startup Page",
                    "Health Overview\nUse search or sidebar to move quickly.",
                ),
                classes="card metric-card",
            ),
        ]
        return (
            Static("Settings", classes="page-title"),
            self.card_grid(cards),
        )

    def about_page(self) -> tuple[object, ...]:
        text = (
            "DevDoctor is a professional Linux workstation health dashboard.\n\n"
            "Keyboard: / search, Tab switch pages, Ctrl+R refresh, Ctrl+E reports, "
            "Ctrl+F auto fix, Esc back, Q quit.\n\n"
            "All checks run without root privileges. Maintenance and install commands are "
            "shown for review and require explicit user confirmation."
        )
        return (
            Static("About", classes="page-title"),
            Static(Panel(text, title="DevDoctor"), classes="card"),
        )

    def result_by_id(self, result_id: str) -> CheckResult | None:
        report = self.report
        if report is None:
            return None
        return next((result for result in report.results if result.id == result_id), None)

    def find_search_target(self, query: str) -> str | None:
        results = self.report.results if self.report else ()
        for result in results:
            exact_terms = {
                result.id.lower(),
                result.title.lower(),
                str(result.details.get("tool", "")).lower(),
            }
            if query in exact_terms:
                return (
                    f"tool:{result.id}"
                    if result.category is CheckCategory.TOOL
                    else _page_for_result(result)
                )
        if len(query) < 3:
            return None
        for result in results:
            haystack = " ".join(
                (
                    result.id,
                    result.title,
                    result.summary,
                    str(result.details.get("tool", "")),
                )
            ).lower()
            if query in haystack:
                return _page_for_result(result)
        for item in NAV_ITEMS:
            haystack = " ".join((item.id, item.title, item.subtitle, *item.keywords)).lower()
            if query in haystack:
                return item.id
        return None

    def action_by_button_id(self, button_id: str) -> MaintenanceAction | None:
        action_id = _unsafe_id(button_id.removeprefix("action-"))
        return next((action for action in optimizer_actions() if action.id == action_id), None)

    def install_plan_by_button_id(self, button_id: str) -> InstallPlan | None:
        tool_id = _unsafe_id(button_id.removeprefix("install-"))
        result = self.result_by_id(tool_id)
        if result is None:
            return None
        return install_plan_for_tool(result.id, result.title)

    def require_report(self) -> HealthReport:
        if self.report is None:
            raise RuntimeError("Report is not available yet.")
        return self.report

    def overview_health_cards(self) -> Grid:
        """Return high-signal workstation health cards for the overview."""

        report = self.require_report()
        info = report.system_info
        cards: list[Static] = []
        definitions = (
            (
                "CPU",
                self.result_by_id("system.cpu"),
                f"{_display_percent(info.get('cpu_usage_percent'))} used\n"
                f"{info.get('logical_cores', 'unknown')} logical cores",
                _as_percent(info.get("cpu_usage_percent")),
            ),
            (
                "RAM",
                self.result_by_id("system.ram"),
                f"{info.get('ram_available', 'unknown')} available\n"
                f"Swap: {_display_percent(info.get('swap_used_percent'))}",
                _as_percent(info.get("ram_used_percent")),
            ),
            (
                "Disk",
                self.result_by_id("system.disk"),
                f"{info.get('disk_free', 'unknown')} free\n"
                f"{info.get('filesystem', 'unknown')} on {info.get('disk_mountpoint', 'unknown')}",
                _as_percent(info.get("disk_used_percent")),
            ),
            (
                "Internet",
                self.result_by_id("network.internet"),
                _result_summary(self.result_by_id("network.internet")),
                None,
            ),
            (
                "DNS",
                self.result_by_id("network.dns"),
                _result_summary(self.result_by_id("network.dns")),
                None,
            ),
            (
                "GitHub",
                self.result_by_id("network.github"),
                _result_summary(self.result_by_id("network.github")),
                None,
            ),
            ("Docker", self.result_by_id("tool.docker"), _tool_line("tool.docker", self), None),
            ("Podman", self.result_by_id("tool.podman"), _tool_line("tool.podman", self), None),
            ("Python", self.result_by_id("tool.python"), _tool_line("tool.python", self), None),
            ("Git", self.result_by_id("tool.git"), _tool_line("tool.git", self), None),
            ("Node.js", self.result_by_id("tool.node"), _tool_line("tool.node", self), None),
            (
                "Platform",
                self.result_by_id("system.os"),
                f"{info.get('distribution', 'unknown')}\nKernel: {info.get('kernel', 'unknown')}",
                None,
            ),
        )
        for title, result, body, percent in definitions:
            cards.append(
                Static(
                    self.health_panel(title, result, body, percent=percent),
                    classes="card metric-card",
                )
            )
        return self.card_grid(cards)

    def health_panel(
        self,
        title: str,
        result: CheckResult | None,
        body: str,
        *,
        percent: float | None = None,
    ) -> Panel:
        """Render a compact status card with an optional utilization bar."""

        status = (
            "Unknown" if result is None else f"{status_icon(result.status)} {result.status.value}"
        )
        parts: list[object] = [Text(status, style="bright_white"), Text(body)]
        if percent is not None:
            parts.append(ProgressBar(total=100, completed=max(0, min(100, percent)), width=24))
        return Panel(
            Group(*parts),
            title=title,
            border_style=_status_border(result),
        )

    def network_detail_lines(self, result: CheckResult) -> tuple[str, ...]:
        """Return concise network details without hiding raw diagnostic value."""

        if result.id == "network.internet":
            probes = result.details.get("probes", ())
            lines = [
                f"{probe.get('host')}:{probe.get('port')} {_latency_label(probe.get('latency_ms'))}"
                for probe in probes
                if isinstance(probe, dict)
            ]
            return tuple(lines[:3])
        if result.id == "network.dns":
            resolved = result.details.get("resolved", {})
            if isinstance(resolved, dict) and resolved:
                return tuple(f"{host} -> {address}" for host, address in resolved.items())
        if result.id == "network.github":
            return (
                f"Address: {result.details.get('address', 'unknown')}",
                f"Latency: {_latency_label(result.details.get('latency_ms'))}",
            )
        return ()

    def summary_cards(self) -> Grid:
        """Return compact score summary cards."""

        report = self.require_report()
        summary = report.summary
        cards = [
            Static(self.metric_panel("Passed", f"✓ {summary.passed}"), classes="card metric-card"),
            Static(
                self.metric_panel("Warnings", f"⚠ {summary.warnings}"), classes="card metric-card"
            ),
            Static(self.metric_panel("Failed", f"✕ {summary.failed}"), classes="card metric-card"),
            Static(
                self.metric_panel("Duration", f"{report.duration_seconds:.2f}s"),
                classes="card metric-card",
            ),
        ]
        return self.card_grid(cards)

    def card_grid(self, cards: list[object]) -> Grid:
        """Return a responsive card grid for the current terminal width."""

        grid = Grid(*cards)
        if self.size.width < 88:
            columns = 1
        elif self.size.width < 132:
            columns = 2
        else:
            columns = 3
        grid.styles.grid_size_columns = columns
        grid.styles.grid_gutter_horizontal = 1
        grid.styles.grid_gutter_vertical = 1
        return grid

    def metric_panel(self, title: str, value: str) -> Panel:
        return Panel(Text(value), title=title, border_style="bright_black")

    def _status_label(self, result: CheckResult | None) -> str:
        if result is None:
            return "Unknown"
        return f"{status_icon(result.status)} {result.status.value}"

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    async def action_next_page(self) -> None:
        current_index = next(
            (index for index, item in enumerate(NAV_ITEMS) if item.id == self.selected_page),
            0,
        )
        for offset in range(1, len(NAV_ITEMS) + 1):
            item = NAV_ITEMS[(current_index + offset) % len(NAV_ITEMS)]
            if item.id != "quit":
                await self.set_page(item.id)
                return

    def action_refresh(self) -> None:
        self.run_scan()

    async def action_show_reports(self) -> None:
        await self.set_page("reports")

    async def action_show_autofix(self) -> None:
        await self.set_page("autofix")

    async def action_back(self) -> None:
        if not self.page_history:
            await self.set_page("overview")
            return
        self.selected_page = self.page_history.pop()
        self.sync_sidebar_selection()
        await self.render_current_page()

    def sync_sidebar_selection(self) -> None:
        """Keep sidebar selection aligned with keyboard navigation."""

        nav = self.query_one("#nav", ListView)
        for index, item in enumerate(NAV_ITEMS):
            if item.id == self.selected_page:
                nav.index = index
                return


def _page_for_result(result: CheckResult) -> str:
    if result.category is CheckCategory.NETWORK:
        return "networking"
    if result.id in {"tool.docker", "tool.podman"}:
        return "containers"
    if result.category is CheckCategory.TOOL:
        return "tools"
    return "system"


def _safe_id(value: str) -> str:
    return value.replace(".", "__")


def _unsafe_id(value: str) -> str:
    return value.replace("__", ".")


def _nav_label(item: NavItem) -> str:
    return f"{NAV_ICONS.get(item.id, '·')} {item.title}"


def _display_percent(value: object) -> str:
    percent = _as_percent(value)
    if percent is None:
        return "unknown"
    return f"{percent:.1f}%"


def _as_percent(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _result_summary(result: CheckResult | None) -> str:
    if result is None:
        return "Not available"
    return result.summary


def _tool_line(result_id: str, app: DevDoctorDashboard) -> str:
    result = app.result_by_id(result_id)
    if result is None:
        return "Not available"
    version = result.details.get("version") or result.details.get("python_version")
    path = result.details.get("path") or result.details.get("python_executable")
    return f"{version or result.summary}\n{path or 'Path not detected'}"


def _status_border(result: CheckResult | None) -> str:
    if result is None:
        return "bright_black"
    return {
        "pass": "green",
        "warning": "yellow",
        "fail": "red",
    }.get(result.status.value, "bright_black")


def _latency_label(value: object) -> str:
    if isinstance(value, int | float):
        return f"{value:.0f} ms"
    return "unreachable"


def _group_install_plans(plans: tuple[InstallPlan, ...]) -> dict[str, list[InstallPlan]]:
    grouped: dict[str, list[InstallPlan]] = {
        "Development": [],
        "Containers": [],
        "Cloud": [],
        "Other": [],
    }
    for plan in plans:
        grouped[_plan_category(plan)].append(plan)
    return {category: items for category, items in grouped.items() if items}


def _plan_category(plan: InstallPlan) -> str:
    if plan.tool_id in {"tool.docker", "tool.podman"}:
        return "Containers"
    if plan.tool_id in {"tool.kubectl", "tool.helm", "tool.terraform", "tool.github_cli"}:
        return "Cloud"
    if plan.tool_id.startswith("tool."):
        return "Development"
    return "Other"


def _plan_estimated_time(plan: InstallPlan) -> str:
    if plan.manager in {"APT", "DNF", "Pacman", "rpm-ostree"}:
        return "2-10 minutes"
    if plan.manager == "Homebrew":
        return "1-8 minutes"
    return "Varies"


def _plan_risk(plan: InstallPlan) -> str:
    if plan.manager == "rpm-ostree":
        return "Medium - layers a system package and usually requires reboot"
    if plan.command.startswith("sudo "):
        return "Medium - requires package-manager privileges"
    return "Low - user-space package install"


def _action_risk(action: MaintenanceAction) -> str:
    if action.requires_sudo:
        return "Medium - requires sudo and package-manager review"
    if action.command.startswith("find /tmp"):
        return "Medium - deletes matching user-owned temporary files"
    return "Low - command asks the tool to confirm or report reclaimed space"


def run_dashboard(*, network_timeout: float = 3.0) -> None:
    """Launch the interactive dashboard."""

    DevDoctorDashboard(network_timeout=network_timeout).run()
