# Checks and Catalog Reference

DevDoctor's default workflow is a bootstrap inventory. Each catalog entry is a typed `ToolSpec`; each probe returns a `ToolDetection`. A failed command probe is recorded as data and does not stop the rest of the inventory.

## Host Context

DevDoctor detects host context from local OS files, environment variables, filesystem state, and safe commands:

- Linux distribution and ID-like family from `/etc/os-release`.
- Architecture from the running OS.
- Desktop and session hints from `XDG_CURRENT_DESKTOP`, `XDG_SESSION_DESKTOP`, `DESKTOP_SESSION`, and `XDG_SESSION_TYPE`.
- Shell and terminal from the process environment.
- Root state and sudo availability.
- WSL, container, and virtualization signals.
- PATH entries and missing PATH directories.
- Installed package managers and their versions where available.

## Tool Detection

For each tool DevDoctor records:

- installed state
- executable name
- executable path
- parsed version
- owning package where `dpkg`, `rpm`, or `pacman` can report it
- existing configuration locations
- official website
- recommended version metadata when the catalog provides it
- broken installation signals
- permission issues
- PATH issues
- missing dependencies
- package-manager install plan

No value is fabricated. If a platform cannot report something reliably, the field is `null`, empty, or omitted from terminal output.

## Built-in Categories

- System
- Programming Languages
- Version Managers
- Package Managers
- Editors
- Containers
- Virtualization
- Databases
- Cloud CLIs
- DevOps
- AI
- Security
- Networking
- Terminal Utilities
- Build Systems
- Package Registries
- Mobile Development
- Game Development
- Compilers
- Debuggers
- Reverse Engineering
- Monitoring
- Shell Enhancements
- Fonts
- Git Utilities
- SSH
- GPG
- System Services

## Package Managers

The install planner can use detected managers from these families:

- APT
- DNF
- rpm-ostree
- Pacman
- yay
- paru
- Zypper
- XBPS
- APK
- Nix
- Homebrew
- Flatpak
- Snap
- Cargo
- Go
- pip
- pipx
- npm
- pnpm
- Yarn
- RubyGems
- Composer
- Rustup
- Flutter
- mise
- asdf

Install plans include the command, a dry-run command when the manager supports one, rollback command when known, verification command, and risk label.

## Profiles

Built-in profiles are intentionally narrow:

- `general`
- `frontend`
- `backend`
- `python`
- `node`
- `rust`
- `go`
- `java`
- `flutter`
- `android`
- `data-science`
- `ai`
- `security`
- `devops`
- `cloud`
- `game`

Profiles select tool IDs from the same catalog used by `devdoctor check`, `install`, and `verify`.

## Plugin Catalog

External packages can register bootstrap tools through the `devdoctor.bootstrap_tools` entry point group. An entry point may return one `ToolSpec` or an iterable of `ToolSpec` instances.

```toml
[project.entry-points."devdoctor.bootstrap_tools"]
workstation_tools = "example_package.devdoctor:get_tools"
```

Plugin catalog entries must be local, fast, and safe to evaluate without root privileges.

## Legacy Health Checks

`devdoctor health` keeps the older `CheckResult` and `HealthReport` model for compatibility. Those checks still cover system information, developer tools, network connectivity, DNS, GitHub reachability, scoring, and JSON/HTML/Markdown/PDF exporters.

The legacy health score is not used by the default bootstrap workflow.
