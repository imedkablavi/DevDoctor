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
            self.summary_cards(),
            Static(
                Panel(recommendations, title="Recommendations", border_style="yellow"),
                classes="card",
            ),
        )

    def system_page(self) -> tuple[object, ...]:
        info = self.require_report().system_info
        card_widgets: list[Static] = []
        for title, key in (
            ("CPU", "cpu"),
            ("RAM", "ram_total"),
            ("GPU", "gpu"),
            ("Disk", "disk_free"),
            ("Kernel", "kernel"),
            ("Distribution", "distribution"),
            ("Hostname", "hostname"),
            ("Architecture", "architecture"),
        ):
            value = info.get(key, "Not available")
            card_widgets.append(Static(self.metric_panel(title, str(value)), classes="card"))
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
        report = self.require_report()
        results = tuple(
            result for result in report.results if result.category is CheckCategory.NETWORK
        )
        cards = [
            Static(
                self.metric_panel(
                    result.title,
                    f"{status_icon(result.status)} {result.summary}\n"
                    f"{result.recommendation or 'No action required.'}",
                ),
                classes="card metric-card",
            )
            for result in results
        ]
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
                        f"{status}\n{manager.path or 'No executable found'}\n{manager.family}",
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
                        f"Estimated freed space: {action.estimated_freed}\n{action.command}"
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
        for plan in plans:
            rows.append(
                Vertical(
                    Static(f"{plan.tool_title}\n{plan.note}\n{plan.command}"),
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


def run_dashboard(*, network_timeout: float = 3.0) -> None:
    """Launch the interactive dashboard."""

    DevDoctorDashboard(network_timeout=network_timeout).run()
