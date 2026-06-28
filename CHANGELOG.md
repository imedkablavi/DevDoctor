# Changelog

All notable changes to DevDoctor are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

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
