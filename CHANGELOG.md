# Changelog

All notable changes to DevDoctor are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

## [1.2.0rc1] - 2026-08-27

### Added

- Fixture-driven package-manager policy coverage for APT, DNF, rpm-ostree, Pacman, Zypper, Nix, Flatpak, and mixed-manager hosts.
- Distro/container integration workflow for Ubuntu/APT, Fedora/DNF, Arch/Pacman, SUSE/Zypper, Nix, Flatpak, and synthetic Atomic policy checks.
- Fedora Atomic and Bazzite install-planning policy that suppresses DNF host mutation and prefers mapped user-space tooling before rpm-ostree layering.
- `manager-conflicts` command for package-manager overlap and Atomic-host policy conflicts.
- `path-conflicts` command for bounded duplicate executable, version, and package-ownership analysis.
- Privacy-scrubbed `diagnostics` export without hostname, username, raw PATH values, arbitrary environment values, or secret/token values.
- Bash, Zsh, and Fish completion generation without editing shell startup files.
- Transaction-journaled repair application and rollback commands with independent confirmation and bounded rollback allowlists.
- Startup/bounded-scan benchmark workflow.
- Python 3.11 through 3.14 clean-wheel installation matrix.
- Release-specific user-space install script that can download the exact GitHub Release wheel and verify it against `SHA256SUMS`.
- Deterministic SPDX 2.3 SBOM generation for release artifacts and declared runtime dependencies.
- GitHub/Sigstore provenance and SBOM attestations for tagged releases.
- PyPI Trusted Publishing path that reuses the exact artifacts produced by the tagged release build.
- Release-candidate notes and evidence-based distribution/readiness documentation.
- Explicit release checks for normalized `devdoctor_workstation` wheel and sdist filenames.

### Changed

- Release candidate version is `1.2.0rc1` and is classified as beta until qualification completes.
- Python distribution identifier is `devdoctor-workstation`; the product and executable remain `DevDoctor` and `devdoctor`.
- The previously planned `devdoctor-cli` distribution identifier was abandoned before first publication because it is already used by another public project.
- GitHub Actions workflows use current Node 24/ESM-generation official actions where available.
- Release tags are rejected when the tag version does not match the package version.
- Release checksum generation is deterministic and excludes the checksum manifest itself.
- README positioning now focuses on diagnosing the existing Linux workstation rather than presenting DevDoctor as another environment manager.
- Documentation distinguishes detection support, fixture verification, container integration, and real-workstation evidence.
- PyPI and Homebrew installation instructions are not presented as available before those external channels are actually published and verified.

### Fixed

- `self-update` now upgrades `devdoctor-workstation` instead of targeting unrelated or occupied package names.
- The user-space installer now resolves `devdoctor_workstation-<version>-py3-none-any.whl` and verifies it against the release checksum manifest.
- Project metadata tests validate the hardened public console entry point, `devdoctor.entrypoint:main`, and the publication distribution name.
- Hardening tests were reformatted so the CI lint gate can reach the actual test suite.
- PATH alternate probing no longer reports a duplicate installation when the primary command lookup says the executable is missing.

### Security

- `uninstall` now fails closed unless the selected executable's detected package ownership matches the catalog mapping.
- RPM ownership on Atomic/Bazzite hosts is not treated as proof that a package is rpm-ostree layered.
- DNF host mutation is suppressed on Fedora Atomic/Bazzite policy paths.
- Repair application and rollback remain preview-first and require explicit apply/confirmation paths.
- Release provenance uses GitHub OIDC/keyless attestations instead of a long-lived signing credential in the repository.
- PyPI publishing uses Trusted Publishing and does not require a long-lived PyPI API token.

## [1.1.0] - 2026-06-28

### Added

- Intelligent tool detection with health states, inferred installation method, alternate executable paths, dependency status, and repair recommendations.
- Dependency graph expansion for selected tools so commands like `devdoctor check flutter` include the related toolchain context.
- Repair recommendations for Docker daemon/socket failures, Git identity configuration, missing SSH public keys, Python without pip, Node.js without npm, Java without `JAVA_HOME`, Cargo PATH gaps, Flutter Android toolchain gaps, broken symlinks, non-executable commands, duplicate executable installations, and missing runtime dependencies.
- PATH analyzer for empty entries, duplicate directories, missing directories, non-directory entries, non-searchable directories, unexported user binary directories, and shadowed executables.
- Richer `devdoctor search` output with category, health, version, installation method, profiles, dependencies, install command, and website.
- Structured JSON Lines operation logging with selected package manager, executed command, exit code, duration, verification command, and verification result.
- Verification-after-execution for install and uninstall plans when the catalog defines a verification command.
- Unit tests for PATH analysis, broken symlink discovery, dependency resolution, repair recommendations, structured operation logs, and command verification logging.

### Changed

- Install plans now show package name, selected package-manager reason, sudo requirement, dependency metadata, verification command, and rollback command when known.
- The bootstrap inventory includes dependency tools in scoped checks and search results, preserving catalog ordering.
- Terminal repair output now explains what happened, why it matters, how to fix it, and how to verify the fix.

### Security

- Mutating command execution remains opt-in through `--apply`, with confirmation unless `--yes` is provided.
- Command execution continues to use argument vectors with `shell=False`.
- Repair suggestions remain read-only and do not modify shell startup files, service state, group membership, or package metadata automatically.

## [1.0.0] - 2026-06-28

### Added

- First stable release of DevDoctor as a Linux developer workstation bootstrap CLI.
- Bootstrap inventory for host context, package managers, developer tools, programming languages, containers, databases, cloud CLIs, DevOps tools, AI tools, security tools, build systems, mobile tooling, game tooling, debuggers, and terminal utilities.
- Distro-aware install plans with dry-run commands, rollback commands, verification commands, and risk labels where the package manager supports them.
- Built-in profiles for general, frontend, backend, Python, Node, Rust, Go, Java, Flutter, Android, data science, AI, security, DevOps, cloud, and game development.
- Safe command execution flow for install, update, uninstall, cache-clean, and self-update operations using explicit `--apply` confirmation.
- JSON, Markdown, and standalone HTML bootstrap inventory exporters.
- Bootstrap catalog extension point through the `devdoctor.bootstrap_tools` entry point group.
- Legacy `devdoctor health` command for non-interactive health reports and JSON/HTML/Markdown/PDF exporters.
- Complete brand asset set with logo, icon, favicon, and GitHub social banner.
- Unit tests for bootstrap install planning, tool detection, PATH repair detection, profile coverage, scoring, version parsing, report generation, package-manager detection, and plugin loading.
- GitHub Actions workflows, issue templates, labels, release template, and pull request template.

### Changed

- `devdoctor` now prints a workstation bootstrap inventory by default.
- `devdoctor --json` now emits bootstrap inventory JSON.
- `devdoctor --quiet` now prints installed, missing, broken, and total counts.
- Project positioning changed from health dashboard to bootstrap and repair CLI.

### Removed

- Removed the Textual dashboard from the public CLI and package dependencies.
- Removed health-score output from the default workflow.

### Security

- Scans are read-only and run as the current user.
- System-changing commands require `--apply` and confirmation unless `--yes` is explicitly provided.
- Command execution uses argument vectors with `shell=False`.
- Operation commands are logged under the user state directory.
