"""Read-only project requirement discovery and workstation compatibility checks."""

from __future__ import annotations

import json
import re
import tomllib
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import typer

from devdoctor.bootstrap import bootstrap_inventory, get_bootstrap_tools

_MAX_MANIFEST_BYTES = 1_000_000
_MAX_CONSTRAINT_CHARS = 256
_MAX_DISPLAY_CHARS = 240
_MAX_REQUIREMENTS = 128
_REGISTERED_APP_IDS: set[int] = set()
_TOOL_ALIASES = {
    "python": "python",
    "python3": "python",
    "node": "node",
    "nodejs": "node",
    "npm": "npm",
    "pnpm": "pnpm",
    "yarn": "yarn",
    "bun": "bun",
    "rust": "rust",
    "rustc": "rust",
    "cargo": "cargo",
    "go": "go",
    "golang": "go",
    "java": "java",
    "ruby": "ruby",
    "php": "php",
    "docker": "docker",
    "terraform": "terraform",
    "kubectl": "kubectl",
}
_ATOM_PATTERN = re.compile(
    r"(>=|<=|==|!=|~=|=|>|<|\^|~)?v?"
    r"(\d+(?:\.\d+){0,3})(?:\.(x|\*))?"
)
_SIMPLE_VERSION_FILES = (
    (".nvmrc", "node"),
    (".node-version", "node"),
    (".python-version", "python"),
    (".ruby-version", "ruby"),
    (".java-version", "java"),
    (".go-version", "go"),
)
_DOCKER_MANIFESTS = (
    "Dockerfile",
    "compose.yml",
    "compose.yaml",
    "docker-compose.yml",
    "docker-compose.yaml",
)
_JAVA_MANIFESTS = ("pom.xml", "build.gradle", "build.gradle.kts")


@dataclass(frozen=True, slots=True)
class ProjectRequirement:
    """One tool requirement declared by a project file."""

    tool_id: str
    source: str
    constraint: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class ProjectCheck:
    """Evaluation of one project requirement against the current workstation."""

    tool_id: str
    source: str
    constraint: str | None
    installed: bool
    installed_version: str | None
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class ProjectReport:
    """Project-level workstation compatibility report."""

    project_name: str
    sources: tuple[str, ...]
    checks: tuple[ProjectCheck, ...]
    warnings: tuple[str, ...]

    @property
    def blocking(self) -> bool:
        return any(check.status in {"missing", "mismatch"} for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project_name": self.project_name,
            "sources": list(self.sources),
            "checks": [asdict(check) for check in self.checks],
            "warnings": list(self.warnings),
            "blocking": self.blocking,
        }


def _safe_display_text(value: object, *, max_chars: int = _MAX_DISPLAY_CHARS) -> str:
    """Remove control characters while bounding work and output memory."""

    rendered: list[str] = []
    for character in str(value):
        if character in {"\n", "\r", "\t"}:
            character = " "
        elif unicodedata.category(character).startswith("C"):
            continue
        rendered.append(character)
        if len(rendered) > max_chars:
            break

    normalized = " ".join("".join(rendered).split())
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return normalized[:max_chars]
    return normalized[: max_chars - 3] + "..."


def _normalize_constraint(constraint: str | None) -> str | None:
    """Keep version expressions bounded and ASCII-safe before comparing them."""

    if not isinstance(constraint, str) or not constraint.strip():
        return None
    if len(constraint) > _MAX_CONSTRAINT_CHARS:
        return "<unsupported: constraint too long>"
    ascii_only = "".join(
        character if 32 <= ord(character) <= 126 else " " for character in constraint
    )
    return " ".join(ascii_only.split()) or None


def _safe_manifest_text(path: Path, *, root: Path) -> tuple[str | None, str | None]:
    """Read a bounded in-project UTF-8 manifest without following symlinks."""

    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return None, "refused manifest outside the selected project root"
    if path.is_symlink():
        return None, f"{relative}: symlinked manifests are not followed"
    try:
        stat = path.stat()
    except OSError as exc:
        return None, f"{relative}: unable to stat manifest ({exc.__class__.__name__})"
    if stat.st_size > _MAX_MANIFEST_BYTES:
        return None, f"{relative}: manifest exceeds {_MAX_MANIFEST_BYTES} bytes"

    try:
        with path.open("r", encoding="utf-8", errors="strict") as handle:
            text = handle.read(_MAX_MANIFEST_BYTES + 1)
    except (OSError, UnicodeError) as exc:
        return None, f"{relative}: unable to read UTF-8 manifest ({exc.__class__.__name__})"
    if len(text) > _MAX_MANIFEST_BYTES:
        return None, f"{relative}: manifest exceeds {_MAX_MANIFEST_BYTES} characters"
    return text, None


def _add_requirement(
    requirements: list[ProjectRequirement],
    *,
    tool: str,
    source: str,
    constraint: str | None,
    reason: str,
) -> None:
    if len(requirements) >= _MAX_REQUIREMENTS:
        return
    tool_id = _TOOL_ALIASES.get(tool.lower())
    if tool_id is None:
        return
    requirement = ProjectRequirement(
        tool_id=tool_id,
        source=source,
        constraint=_normalize_constraint(constraint),
        reason=reason,
    )
    if requirement not in requirements:
        requirements.append(requirement)


def _has_requirement(
    requirements: list[ProjectRequirement],
    *,
    tool: str,
    source: str,
) -> bool:
    tool_id = _TOOL_ALIASES.get(tool.lower())
    return any(item.tool_id == tool_id and item.source == source for item in requirements)


def _parse_pyproject(
    text: str,
    requirements: list[ProjectRequirement],
    warnings: list[str],
) -> None:
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        warnings.append("pyproject.toml: invalid TOML")
        return

    recognized = False
    project = document.get("project")
    if isinstance(project, dict):
        recognized = True
        requires_python = project.get("requires-python")
        if isinstance(requires_python, str):
            _add_requirement(
                requirements,
                tool="python",
                source="pyproject.toml",
                constraint=requires_python,
                reason="project.requires-python",
            )

    tool = document.get("tool")
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            recognized = True
            dependencies = poetry.get("dependencies")
            if isinstance(dependencies, dict):
                python_constraint = dependencies.get("python")
                if isinstance(python_constraint, str):
                    _add_requirement(
                        requirements,
                        tool="python",
                        source="pyproject.toml",
                        constraint=python_constraint,
                        reason="tool.poetry.dependencies.python",
                    )

    if recognized and not _has_requirement(
        requirements,
        tool="python",
        source="pyproject.toml",
    ):
        _add_requirement(
            requirements,
            tool="python",
            source="pyproject.toml",
            constraint=None,
            reason="Python project metadata",
        )


def _parse_package_json(
    text: str,
    requirements: list[ProjectRequirement],
    warnings: list[str],
) -> None:
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        warnings.append("package.json: invalid JSON")
        return
    if not isinstance(document, dict):
        warnings.append("package.json: top-level JSON value is not an object")
        return

    engines = document.get("engines")
    if isinstance(engines, dict):
        for tool in ("node", "npm", "pnpm", "yarn", "bun"):
            constraint = engines.get(tool)
            if isinstance(constraint, str):
                _add_requirement(
                    requirements,
                    tool=tool,
                    source="package.json",
                    constraint=constraint,
                    reason=f"engines.{tool}",
                )

    package_manager = document.get("packageManager")
    if isinstance(package_manager, str) and "@" in package_manager:
        manager, version = package_manager.split("@", 1)
        version = version.split("+", 1)[0]
        if manager in {"npm", "pnpm", "yarn", "bun"} and version:
            _add_requirement(
                requirements,
                tool=manager,
                source="package.json",
                constraint=version,
                reason="packageManager",
            )

    volta = document.get("volta")
    if isinstance(volta, dict):
        for tool in ("node", "npm", "pnpm", "yarn"):
            version = volta.get(tool)
            if isinstance(version, str):
                _add_requirement(
                    requirements,
                    tool=tool,
                    source="package.json",
                    constraint=version,
                    reason=f"volta.{tool}",
                )

    if not _has_requirement(requirements, tool="node", source="package.json"):
        _add_requirement(
            requirements,
            tool="node",
            source="package.json",
            constraint=None,
            reason="Node project manifest",
        )


def _parse_tool_versions(text: str, requirements: list[ProjectRequirement]) -> None:
    for raw_line in text.splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 2 or parts[0].startswith("#"):
            continue
        _add_requirement(
            requirements,
            tool=parts[0],
            source=".tool-versions",
            constraint=parts[1],
            reason="version-manager declaration",
        )
        if len(requirements) >= _MAX_REQUIREMENTS:
            return


def _mise_constraint(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value and isinstance(value[0], str):
        return value[0]
    if isinstance(value, dict) and isinstance(value.get("version"), str):
        return value["version"]
    return None


def _parse_mise(
    text: str,
    *,
    source: str,
    requirements: list[ProjectRequirement],
    warnings: list[str],
) -> None:
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        warnings.append(f"{source}: invalid TOML")
        return
    tools = document.get("tools")
    if not isinstance(tools, dict):
        return
    for tool, value in tools.items():
        constraint = _mise_constraint(value)
        if constraint is not None:
            _add_requirement(
                requirements,
                tool=str(tool),
                source=source,
                constraint=constraint,
                reason="mise tools declaration",
            )
        if len(requirements) >= _MAX_REQUIREMENTS:
            return


def _parse_cargo(
    text: str,
    requirements: list[ProjectRequirement],
    warnings: list[str],
) -> None:
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        warnings.append("Cargo.toml: invalid TOML")
        return

    package = document.get("package")
    if isinstance(package, dict) and isinstance(package.get("rust-version"), str):
        _add_requirement(
            requirements,
            tool="rust",
            source="Cargo.toml",
            constraint=f">={package['rust-version']}",
            reason="package.rust-version minimum",
        )
    if not _has_requirement(requirements, tool="rust", source="Cargo.toml"):
        _add_requirement(
            requirements,
            tool="rust",
            source="Cargo.toml",
            constraint=None,
            reason="Rust package manifest",
        )
    _add_requirement(
        requirements,
        tool="cargo",
        source="Cargo.toml",
        constraint=None,
        reason="Cargo project manifest",
    )


def _parse_go_mod(text: str, requirements: list[ProjectRequirement]) -> None:
    match = re.search(r"(?m)^go\s+([0-9]+(?:\.[0-9]+){1,2})\s*$", text)
    _add_requirement(
        requirements,
        tool="go",
        source="go.mod",
        constraint=f">={match.group(1)}" if match else None,
        reason="go language version" if match else "Go module manifest",
    )


def _parse_devbox(
    text: str,
    requirements: list[ProjectRequirement],
    warnings: list[str],
) -> None:
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        warnings.append("devbox.json: invalid JSON")
        return
    if not isinstance(document, dict):
        return

    packages = document.get("packages")
    if isinstance(packages, list):
        values = (value for value in packages if isinstance(value, str))
    elif isinstance(packages, dict):
        values = (str(value) for value in packages)
    else:
        return

    for package in values:
        name, separator, version = package.partition("@")
        if name.lower() in _TOOL_ALIASES:
            _add_requirement(
                requirements,
                tool=name,
                source="devbox.json",
                constraint=version if separator and version != "latest" else None,
                reason="Devbox package declaration",
            )
        if len(requirements) >= _MAX_REQUIREMENTS:
            return


def discover_project_requirements(
    root: Path,
) -> tuple[tuple[ProjectRequirement, ...], tuple[str, ...], tuple[str, ...]]:
    """Discover supported declarative requirements without executing project code."""

    project_root = root.expanduser().resolve()
    if not project_root.is_dir():
        display_path = _safe_display_text(root)
        raise ValueError(f"project path is not a directory: {display_path}")

    requirements: list[ProjectRequirement] = []
    warnings: list[str] = []
    sources: list[str] = []

    def read(name: str) -> str | None:
        path = project_root / name
        if not path.exists() and not path.is_symlink():
            return None
        text, warning = _safe_manifest_text(path, root=project_root)
        if warning:
            warnings.append(warning)
            return None
        sources.append(name)
        return text

    text = read("pyproject.toml")
    if text is not None:
        _parse_pyproject(text, requirements, warnings)

    text = read("package.json")
    if text is not None:
        _parse_package_json(text, requirements, warnings)

    text = read(".tool-versions")
    if text is not None:
        _parse_tool_versions(text, requirements)

    for name in ("mise.toml", ".mise.toml"):
        text = read(name)
        if text is not None:
            _parse_mise(text, source=name, requirements=requirements, warnings=warnings)

    text = read("Cargo.toml")
    if text is not None:
        _parse_cargo(text, requirements, warnings)

    text = read("go.mod")
    if text is not None:
        _parse_go_mod(text, requirements)

    text = read("devbox.json")
    if text is not None:
        _parse_devbox(text, requirements, warnings)

    for name, tool in _SIMPLE_VERSION_FILES:
        text = read(name)
        if text is None:
            continue
        value = next((line.strip() for line in text.splitlines() if line.strip()), "")
        if value:
            _add_requirement(
                requirements,
                tool=tool,
                source=name,
                constraint=value.removeprefix("v"),
                reason="project version file",
            )

    for name in _DOCKER_MANIFESTS:
        if read(name) is not None:
            _add_requirement(
                requirements,
                tool="docker",
                source=name,
                constraint=None,
                reason="container project manifest",
            )

    if read("Gemfile") is not None:
        _add_requirement(
            requirements,
            tool="ruby",
            source="Gemfile",
            constraint=None,
            reason="Ruby dependency manifest",
        )

    if read("composer.json") is not None:
        _add_requirement(
            requirements,
            tool="php",
            source="composer.json",
            constraint=None,
            reason="PHP dependency manifest",
        )

    for name in _JAVA_MANIFESTS:
        if read(name) is not None:
            _add_requirement(
                requirements,
                tool="java",
                source=name,
                constraint=None,
                reason="Java build manifest",
            )

    if len(requirements) >= _MAX_REQUIREMENTS:
        warnings.append(
            f"project requirement limit reached ({_MAX_REQUIREMENTS}); additional entries ignored"
        )
    return tuple(requirements), tuple(sources), tuple(warnings)


def _numeric_version(value: str | None) -> tuple[int, ...] | None:
    if not value:
        return None
    safe_value = _safe_display_text(value, max_chars=128)
    match = re.search(r"\d+(?:\.\d+){0,3}", safe_value)
    if not match:
        return None
    return tuple(int(part) for part in match.group(0).split("."))


def _padded(version: tuple[int, ...], width: int) -> tuple[int, ...]:
    return version + (0,) * max(0, width - len(version))


def _compare(left: tuple[int, ...], right: tuple[int, ...]) -> int:
    width = max(len(left), len(right), 3)
    left_value = _padded(left, width)
    right_value = _padded(right, width)
    return (left_value > right_value) - (left_value < right_value)


def _compatible_upper_bound(required: tuple[int, ...]) -> tuple[int, ...] | None:
    if len(required) < 2:
        return None
    prefix = list(required[:-1])
    prefix[-1] += 1
    return tuple([*prefix, 0])


def _satisfies_atom(installed: tuple[int, ...], atom: str) -> bool | None:
    value = atom.strip().lower().replace(" ", "")
    if not value or value in {"*", "latest", "system"}:
        return True

    match = _ATOM_PATTERN.fullmatch(value)
    if not match:
        return None
    operator = match.group(1) or ""
    required = tuple(int(part) for part in match.group(2).split("."))
    wildcard = match.group(3)

    if wildcard is not None or not operator:
        return installed[: len(required)] == required

    comparison = _compare(installed, required)
    if operator in {"=", "=="}:
        return comparison == 0
    if operator == "!=":
        return comparison != 0
    if operator == ">=":
        return comparison >= 0
    if operator == ">":
        return comparison > 0
    if operator == "<=":
        return comparison <= 0
    if operator == "<":
        return comparison < 0
    if operator == "^":
        major = required[0]
        if major > 0:
            upper = (major + 1, 0, 0)
        elif len(required) > 1 and required[1] > 0:
            upper = (0, required[1] + 1, 0)
        else:
            patch = required[2] if len(required) > 2 else 0
            upper = (0, 0, patch + 1)
        return comparison >= 0 and _compare(installed, upper) < 0
    if operator == "~":
        upper = (
            (required[0], required[1] + 1, 0)
            if len(required) > 1
            else (required[0] + 1, 0, 0)
        )
        return comparison >= 0 and _compare(installed, upper) < 0
    if operator == "~=":
        upper = _compatible_upper_bound(required)
        if upper is None:
            return None
        return comparison >= 0 and _compare(installed, upper) < 0
    return None


def version_satisfies(
    installed_version: str | None,
    constraint: str | None,
) -> bool | None:
    """Evaluate common numeric constraints conservatively."""

    if constraint is None:
        return True
    normalized = _normalize_constraint(constraint)
    if normalized is None or normalized.lower() in {"", "*", "latest", "system"}:
        return True
    if normalized.startswith("<unsupported:"):
        return None

    installed = _numeric_version(installed_version)
    if installed is None:
        return None

    results: list[bool | None] = []
    for alternative in normalized.split("||"):
        group = alternative.strip()
        if not group:
            continue
        if re.search(r"\s-\s", group):
            results.append(None)
            continue
        atoms = [atom for atom in re.split(r"[\s,]+", group) if atom]
        atom_results = [_satisfies_atom(installed, atom) for atom in atoms]
        if any(result is None for result in atom_results):
            results.append(None)
        else:
            results.append(all(bool(result) for result in atom_results))

    if any(result is True for result in results):
        return True
    if results and all(result is False for result in results):
        return False
    return None


def diagnose_project(root: Path) -> ProjectReport:
    """Compare discovered project requirements with local tool detections."""

    project_root = root.expanduser().resolve()
    requirements, sources, warnings = discover_project_requirements(project_root)
    project_name = _safe_display_text(project_root.name, max_chars=120) or "project"
    if not requirements:
        return ProjectReport(project_name, sources, (), warnings)

    catalog_ids = {spec.id for spec in get_bootstrap_tools()}
    requested_ids = tuple(
        sorted(
            {
                requirement.tool_id
                for requirement in requirements
                if requirement.tool_id in catalog_ids
            }
        )
    )
    inventory = bootstrap_inventory(include_ids=requested_ids) if requested_ids else None
    detections = (
        {detection.spec.id: detection for detection in inventory.detections}
        if inventory is not None
        else {}
    )

    checks: list[ProjectCheck] = []
    for requirement in requirements:
        if requirement.tool_id not in catalog_ids:
            checks.append(
                ProjectCheck(
                    tool_id=requirement.tool_id,
                    source=requirement.source,
                    constraint=requirement.constraint,
                    installed=False,
                    installed_version=None,
                    status="unknown",
                    message="tool is not represented by the current DevDoctor catalog",
                )
            )
            continue

        detection = detections.get(requirement.tool_id)
        if detection is None or not detection.installed:
            checks.append(
                ProjectCheck(
                    tool_id=requirement.tool_id,
                    source=requirement.source,
                    constraint=requirement.constraint,
                    installed=False,
                    installed_version=None,
                    status="missing",
                    message="required tool is not installed or discoverable on PATH",
                )
            )
            continue

        satisfies = version_satisfies(detection.version, requirement.constraint)
        if satisfies is True:
            status = "ready"
            message = "installed tool satisfies the discovered requirement"
        elif satisfies is False:
            status = "mismatch"
            message = "installed version does not satisfy the discovered requirement"
        else:
            status = "unknown"
            message = "installed tool was found, but the version constraint is not safely comparable"
        installed_version = _safe_display_text(detection.version) if detection.version else None
        checks.append(
            ProjectCheck(
                tool_id=requirement.tool_id,
                source=requirement.source,
                constraint=requirement.constraint,
                installed=True,
                installed_version=installed_version,
                status=status,
                message=message,
            )
        )

    return ProjectReport(project_name, sources, tuple(checks), warnings)


def render_project_report(report: ProjectReport) -> str:
    """Render a compact, copyable project compatibility report."""

    lines = [f"DevDoctor project check: {report.project_name}"]
    if report.sources:
        lines.append(f"Sources: {', '.join(report.sources)}")
    if not report.checks:
        lines.append("No supported project tool requirements were found.")
    else:
        labels = {
            "ready": "READY",
            "missing": "MISSING",
            "mismatch": "MISMATCH",
            "unknown": "UNKNOWN",
        }
        for check in report.checks:
            constraint = check.constraint or "installed"
            version = check.installed_version or "not found"
            lines.append(
                f"{labels[check.status]:8} {check.tool_id:10} found={version} "
                f"required={constraint} source={check.source}"
            )
    lines.extend(f"WARNING  {warning}" for warning in report.warnings)
    return "\n".join(lines) + "\n"


def register_project_diagnostics_command(app: typer.Typer) -> None:
    """Register the read-only project compatibility command once."""

    if id(app) in _REGISTERED_APP_IDS:
        return
    _REGISTERED_APP_IDS.add(id(app))

    @app.command("project")
    def project(
        path: Path = typer.Argument(Path("."), help="Project directory to inspect."),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Print machine-readable JSON.",
        ),
        no_fail: bool = typer.Option(
            False,
            "--no-fail",
            help="Return exit code 0 even when required tools are missing or incompatible.",
        ),
    ) -> None:
        """Compare project-declared tool versions with the current workstation."""

        try:
            report = diagnose_project(path)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

        if json_output:
            typer.echo(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        else:
            typer.echo(render_project_report(report), nl=False)
        if report.blocking and not no_fail:
            raise typer.Exit(code=1)
