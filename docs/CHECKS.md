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
- inferred installation method
- dependency status for related tools
- health state
- repair recommendations
- broken installation signals
- permission issues
- PATH issues
- missing dependencies
- package-manager install plan

No value is fabricated. If a platform cannot report something reliably, the field is `null`, empty, or omitted from terminal output.

## Health States

The bootstrap workflow uses four health states:

- `ready`: a usable executable was found and no local issue was detected.
- `missing`: no usable executable was found.
- `warning`: the executable exists, but DevDoctor found a configuration, dependency, daemon, or PATH concern that should be reviewed.
- `broken`: the command resolves to an unusable local filesystem entry, such as a broken symlink or a file without executable permission.

Warnings and broken states are derived from local evidence. They are not guessed from package names or expected versions.

## Dependency Engine

Catalog entries may declare required or optional tool dependencies. The inventory resolves those relationships and reports each dependency with:

- tool ID and title
- required or optional state
- installed state
- dependency health
- reason the dependency matters
- install plan for missing dependencies when one is available

Selecting a single tool also includes its required dependency graph in the detection context, so `devdoctor check flutter` can explain missing Git, Java, ADB, and Android SDK command-line tools without requiring those IDs on the command line. Search may include optional dependency context because it is informational and does not drive verification exit status.

## Repair Recommendations

Repair recommendations contain:

- problem
- reason
- risk
- repair command or manual action
- verification command
- rollback command when one is known

The `repair` command is read-only. DevDoctor prints recommendations; it does not execute them.

Current repair checks include Docker daemon and socket failures, Git identity configuration, missing SSH public keys, Python without pip, Node.js without npm, Java without `JAVA_HOME`, Cargo PATH gaps, Flutter Android toolchain gaps, broken symlinks, non-executable commands, duplicate executable installations, and missing runtime dependencies.

## PATH Analyzer

The host context includes a complete PATH analysis:

- empty PATH entries
- duplicate entries
- missing directories
- entries that are not directories
- non-searchable directories
- common user binary directories that exist but are not exported
- shadowed executables

Suggested export commands are included only when DevDoctor can infer a safe command from the current PATH value.

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

Install plans include the selected manager, manager selection reason, package name, command, dry-run command when the manager supports one, rollback command when known, verification command, risk label, sudo requirement, and dependency metadata.

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
