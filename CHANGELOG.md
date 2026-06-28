# Changelog

All notable changes to DevDoctor are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

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
