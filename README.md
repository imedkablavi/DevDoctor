<p align="center">
  <img src="https://raw.githubusercontent.com/imedkablavi/DevDoctor/main/assets/brand/github-social-banner.png" alt="DevDoctor" width="100%">
</p>

<p align="center">
  <a href="https://github.com/imedkablavi/DevDoctor/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/imedkablavi/DevDoctor/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/imedkablavi/DevDoctor/actions/workflows/code-quality.yml"><img alt="Code Quality" src="https://github.com/imedkablavi/DevDoctor/actions/workflows/code-quality.yml/badge.svg"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-22D3EE">
  <img alt="Linux" src="https://img.shields.io/badge/platform-Linux-34D399">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-8EA4BD"></a>
</p>

<h1 align="center">DevDoctor</h1>

<p align="center">
  <strong>Diagnose broken Linux developer workstations before changing them.</strong>
</p>

DevDoctor inspects the Linux workstation you already have, finds missing or broken developer tooling, explains package-manager and PATH conflicts, and builds distro-aware repair or install plans that are previewed before execution.

It does not replace your package manager and it is not another environment manager. The goal is specific: identify what is wrong, show the local evidence, and produce the safest supported next step.

Scans are read-only. Mutating commands require an explicit apply path and confirmation. When ownership or host policy is ambiguous, DevDoctor refuses instead of guessing.

## Demo

<p align="center">
  <img src="https://raw.githubusercontent.com/imedkablavi/DevDoctor/main/assets/screenshots/devdoctor-demo.gif" alt="DevDoctor terminal demonstration" width="100%">
</p>

The demo is generated from real command output. See [assets/screenshots](assets/screenshots/README.md) for regeneration notes.

## Example

```text
$ devdoctor check --profile devops --missing

DevDoctor  v1.2.0rc1          4 installed  7 missing  2 warnings  0 broken
Linux developer workstation bootstrap

Host
OS             Fedora Linux 42        Arch        x86_64
Shell          bash                   Desktop     GNOME
Session        wayland                Terminal    xterm-256color
Managers       dnf, flatpak, pip      PATH issues 1

Containers
! Docker       warning    29.0.0      /usr/bin/docker
  Repair: Docker daemon is not running
  Verify: docker info

DevOps
✗ kubectl                                     sudo dnf install kubernetes-client
✗ Helm                                        sudo dnf install helm
✗ Terraform                                   sudo dnf install terraform
```

Typical findings include Docker daemon failures, missing runtime dependencies, broken executable symlinks, duplicate PATH installations, conflicting package managers, missing Git identity, incomplete Android/Flutter tooling, Java without `JAVA_HOME`, Python without working pip, and user-space binaries that are not exported into PATH.

## Install

DevDoctor requires Python 3.11 or newer.

The product name is **DevDoctor**. The console command is **`devdoctor`**. The Python distribution prepared for publication is **`devdoctor-workstation`**.

> `devdoctor-cli` is not this project's distribution name. Do not use it to install or update this repository.

### Current repository build

Until the first `devdoctor-workstation` PyPI release is published and verified, install directly from this repository:

```bash
python -m pip install "git+https://github.com/imedkablavi/DevDoctor.git"
devdoctor --version
```

For development:

```bash
git clone https://github.com/imedkablavi/DevDoctor.git
cd DevDoctor
python -m pip install -e ".[dev]"
```

A PyPI Trusted Publishing workflow is prepared for tagged releases. The README intentionally does not advertise `pip install devdoctor-workstation` until the public PyPI project has been created, published, and verified.

The Homebrew formula is also release-readiness work. Do not rely on a Homebrew install command until a tap exists and its clean installation CI passes.

## Quick start

```bash
devdoctor
devdoctor check --profile general
devdoctor check git docker node
devdoctor search docker
devdoctor repair docker
devdoctor diagnostics --stdout
devdoctor manager-conflicts
devdoctor path-conflicts git python node
```

Preview installation work without changing the machine:

```bash
devdoctor install git docker --dry-run
devdoctor install --profile devops
```

Execute only after reviewing the plan:

```bash
devdoctor install --profile frontend --apply
```

## Commands

| Command | Purpose |
| --- | --- |
| `devdoctor` | Full workstation inventory. |
| `devdoctor check [tools...]` | Inspect selected tools, a category, or a profile. |
| `devdoctor doctor [tools...]` | Run a focused workstation check. |
| `devdoctor install [tools...]` | Preview or run distro-aware install plans. |
| `devdoctor repair [tools...]` | Show repair evidence and recommendations. |
| `devdoctor repair-apply [tools...]` | Preview or apply rollback-capable repair actions. |
| `devdoctor repair-rollback TRANSACTION_ID` | Preview or apply a persisted rollback transaction. |
| `devdoctor verify [tools...]` | Exit non-zero when selected tools need attention. |
| `devdoctor search QUERY` | Search the local tool catalog. |
| `devdoctor manager-conflicts` | Report suspicious package-manager overlap. |
| `devdoctor path-conflicts [executables...]` | Report duplicate/version/ownership PATH conflicts. |
| `devdoctor diagnostics` | Export a privacy-scrubbed support snapshot. |
| `devdoctor completion SHELL` | Generate Bash, Zsh, or Fish completion text. |
| `devdoctor benchmark` | Measure a bounded local scan. |
| `devdoctor export json` | Export inventory JSON. |
| `devdoctor export markdown` | Export inventory Markdown. |
| `devdoctor update` | Preview package-manager update commands. |
| `devdoctor uninstall TOOL` | Remove only when installed ownership can be proven. |
| `devdoctor cache clean` | Preview supported package cache cleanup commands. |
| `devdoctor self-update` | Preview an update of the `devdoctor-workstation` distribution. |
| `devdoctor health` | Run the legacy health-style report and exporters. |

## Profiles

Profiles keep setup focused instead of installing every tool in a category.

```bash
devdoctor list profiles
devdoctor check --profile python
devdoctor install --profile cloud --dry-run
devdoctor verify --profile general
```

Built-in profiles include `general`, `frontend`, `backend`, `python`, `node`, `rust`, `go`, `java`, `flutter`, `android`, `data-science`, `ai`, `security`, `devops`, `cloud`, and `game`.

## Detection coverage

| Area | Examples |
| --- | --- |
| System | Distribution, architecture, desktop, session, shell, terminal, WSL, containers, virtualization, sudo availability, PATH issues. |
| Package managers | APT, DNF, rpm-ostree, Pacman, yay, paru, Zypper, XBPS, APK, Nix, Flatpak, Snap, Homebrew, Cargo, Go, pip, pipx, npm, pnpm, Yarn, Gem, Composer, Rustup, Flutter, mise, asdf. |
| Languages | Python, Node.js, Bun, Rust, Go, Java, .NET, PHP, Ruby. |
| Editors | Visual Studio Code, Vim, Neovim. |
| Containers and DevOps | Docker, Podman, Distrobox, kubectl, Helm, Terraform, Ansible. |
| Cloud CLIs | GitHub CLI, AWS CLI, Azure CLI, Google Cloud CLI. |
| Data and services | PostgreSQL client, MySQL client, SQLite, Redis CLI, systemd. |
| Security and debugging | OpenSSH, GnuPG, UFW, Nmap, GDB, strace, radare2. |
| Terminal and build tools | curl, wget, jq, ripgrep, fd, fzf, Starship, GCC, Clang, Make, CMake, Ninja. |
| Mobile, AI, and games | Android Debug Bridge, Flutter, Ollama, CUDA compiler, Godot. |

For each tool DevDoctor can record installed state, executable path, parsed version, package ownership where the host can prove it, inferred installation method, configuration locations, dependency state, health, repair recommendations, and an install plan when a safe mapping exists.

Detection support is not the same as mutation support. See [distribution support evidence](docs/SUPPORTED_DISTROS.md) for the distinction between fixtures, clean-wheel checks, container integration, and real-workstation evidence.

## Fedora Atomic and Bazzite

Image-based Fedora derivatives need different rules from mutable Fedora. DevDoctor suppresses DNF host mutation on Fedora Atomic and Bazzite even when a `dnf` executable is present.

Where mappings exist, the planner prefers appropriate user-space tooling first and uses rpm-ostree layering as a host fallback. Synthetic Atomic/Bazzite container tests validate policy only. They are not presented as real workstation or hardware compatibility testing.

## Repair and rollback

Ordinary `repair` is advisory. `repair-apply` only exposes repair actions that include an executable command and a known rollback command. It previews by default and requires `--apply` before execution.

Applied actions are recorded in a transaction journal. `repair-rollback` requires the transaction ID, validates persisted rollback commands against a bounded allowlist, previews them, and requires a separate apply decision.

## PATH and package ownership

The PATH analyzer reports empty entries, duplicates, missing directories, non-searchable directories, common user binary directories that are not exported, and shadowed executables.

`path-conflicts` adds bounded version and package-ownership probes for duplicate executable names. `uninstall` uses a stricter rule: it refuses removal unless the executable owner can be matched to the catalog package. On Atomic systems, RPM ownership by itself is not considered proof that a package was rpm-ostree layered.

## Diagnostics and privacy

```bash
devdoctor diagnostics --stdout | python -m json.tool
devdoctor diagnostics --output devdoctor-diagnostics.json
```

The support snapshot intentionally omits hostname, username, raw PATH values, arbitrary environment values, and secret/token values. Review diagnostic files before sharing them because package and version names can still reveal local environment details.

## Export formats

```bash
devdoctor --json > inventory.json
devdoctor --json-file inventory.json
devdoctor --markdown-file inventory.md
devdoctor --html-file inventory.html
devdoctor export json --output inventory.json
devdoctor export markdown --output inventory.md
```

JSON is the machine-readable inventory format. Markdown is useful for issues, handoffs, and onboarding notes. HTML is a standalone local report.

## Safety model

- Scans, search, diagnostics, conflict analysis, and ordinary repair inspection are read-only.
- DevDoctor does not use `shell=True` for its planned command execution path.
- Install, update, uninstall, cache cleanup, self-update, repair application, and rollback are preview-first.
- `--apply` is required for supported mutation paths.
- Confirmation remains enabled unless the user explicitly passes `--yes`.
- Fedora Atomic/Bazzite host planning does not fall back to DNF mutation.
- Ambiguous package ownership causes uninstall to refuse rather than select a package manager by guesswork.
- Executed operations are recorded as structured JSON Lines in the user state directory.
- Verification commands run after successful operations when the plan provides one.
- Diagnostics are designed not to export secrets, credentials, shell history, hostname, username, or raw environment values.

## Architecture

```mermaid
flowchart LR
  CLI[Typer CLI] --> Catalog[Tool Catalog]
  Catalog --> Builtins[Built-in ToolSpec entries]
  Catalog --> Plugins[devdoctor.bootstrap_tools entry points]
  CLI --> Detector[Isolated Detectors]
  Detector --> Inventory[BootstrapInventory]
  Inventory --> Terminal[Rich Terminal Output]
  Inventory --> Exporters[JSON / Markdown / HTML]
  Inventory --> Policy[Package-manager safety policy]
  Policy --> Planner[Install / Update / Repair Plans]
  Planner --> Executor[Confirmed subprocess execution]
  Executor --> Verify[Verification + operation log]
```

The bootstrap model is centered on `ToolSpec`, `ToolDetection`, `InstallPlan`, `BootstrapProfile`, and `BootstrapInventory`. The current release candidate also has a conservative compatibility layer around older planners and mutating callbacks. Moving those policies into one central planner/executor API remains architecture cleanup work.

## Plugin catalog

Third-party packages can add bootstrap tools through the `devdoctor.bootstrap_tools` entry-point group.

```toml
[project.entry-points."devdoctor.bootstrap_tools"]
mytools = "my_package.devdoctor:get_tools"
```

Plugin detectors should be fast, local, non-destructive, and safe to run without root privileges.

## Release verification

The `v1.2.0rc1` release pipeline is designed to build the Python distributions once, validate the clean wheel, generate `SHA256SUMS` and an SPDX 2.3 SBOM, create provenance/SBOM attestations, and then reuse those tested artifacts for GitHub Release and optional PyPI Trusted Publishing.

Expected release payload:

```text
devdoctor_workstation-1.2.0rc1-py3-none-any.whl
devdoctor_workstation-1.2.0rc1.tar.gz
devdoctor-install.sh
devdoctor.spdx.json
SHA256SUMS
```

PyPI publication remains disabled until the external Trusted Publisher for `devdoctor-workstation` and the protected `pypi` environment are configured. See [release distribution readiness](docs/RELEASE_DISTRIBUTION.md) and [v1.2.0rc1 release notes](docs/RELEASE_NOTES_v1.2.0rc1.md).

## Development

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
pytest
python -m devdoctor --quiet
python -m devdoctor --json | python -m json.tool
```

When changing package mappings, package identity, or safety policy, add deterministic positive and negative tests. When changing CLI output, verify terminal output and machine-readable JSON.

## Roadmap

- Qualify and publish the release candidate after the final commit passes the full matrix.
- Configure the external PyPI Trusted Publisher for `devdoctor-workstation` and protected GitHub `pypi` environment.
- Publish and validate a Homebrew tap instead of advertising a future command prematurely.
- Move temporary runtime policy overrides into a single central planner/executor architecture.
- Expand real-workstation evidence for Atomic/Bazzite and other advertised environments.
- Add project-aware diagnosis for `pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, containers, and version-manager files.
- Add more verified distro package mappings through contribution fixtures.
- Publish an external plugin example and stable bootstrap JSON schema documentation.

## FAQ

**Does DevDoctor install packages by default?**  
No. Inventory and planning are read-only. A supported mutation requires an explicit apply path.

**Why not show one workstation score?**  
A workstation is only ready relative to the project in front of it. DevDoctor reports concrete installed, missing, warning, and broken states instead of hiding them behind one score.

**Can I use it in CI or onboarding scripts?**  
Yes. `devdoctor verify --profile general --quiet` gives an exit status; `devdoctor --json` gives structured inventory data.

**Does it support non-Linux systems?**  
No. DevDoctor is intentionally Linux-first.

## Documentation

- [CLI reference](docs/CLI_REFERENCE.md)
- [Usage](docs/USAGE.md)
- [Checks and catalog reference](docs/CHECKS.md)
- [Distribution support evidence](docs/SUPPORTED_DISTROS.md)
- [Release distribution readiness](docs/RELEASE_DISTRIBUTION.md)
- [v1.2.0rc1 release notes](docs/RELEASE_NOTES_v1.2.0rc1.md)
- [Examples](examples/README.md)
- [Accessibility](docs/ACCESSIBILITY.md)
- [Brand system](docs/BRAND.md)
- [Release process](docs/RELEASE.md)
- [Release readiness](RELEASE_READINESS.md)
- [Roadmap](ROADMAP.md)
- [Migration guide](MIGRATION_GUIDE.md)
- [Security policy](SECURITY.md)
- [Support](SUPPORT.md)

## Contributing

Contributions are welcome when they keep DevDoctor local-first, Linux-focused, testable, and honest about unavailable evidence. Start with [CONTRIBUTING.md](CONTRIBUTING.md), run the validation commands, and include terminal output or fixtures for user-facing package-manager changes.

## Credits

DevDoctor uses [Typer](https://typer.tiangolo.com/), [Rich](https://rich.readthedocs.io/), [psutil](https://psutil.readthedocs.io/), and [platformdirs](https://platformdirs.readthedocs.io/).

## License

DevDoctor is released under the MIT License. See [LICENSE](LICENSE).
