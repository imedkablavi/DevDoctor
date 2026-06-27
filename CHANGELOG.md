# Changelog

All notable changes to DevDoctor are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [1.0.0] - 2026-06-28

### Added

- First stable release of DevDoctor.
- Interactive Textual dashboard with sidebar navigation, search, background scans, tool cards, detailed tool pages, report actions, optimizer actions, and Auto Fix command previews.
- Isolated checks for system information, developer tools, network connectivity, DNS, and GitHub reachability.
- Plugin metadata registry for built-in and future external checks.
- Package-manager detection and distro-aware install command planning.
- Weighted health scoring with actionable recommendations.
- JSON, standalone HTML, Markdown, and compact PDF report exporters.
- Complete brand system with SVG and PNG assets, GitHub social banner, favicon, app icon, and animated preview.
- Unit tests for scoring, tool detection, version parsing, and report generation.
- GitHub Actions workflows, issue templates, and pull request template.

### Changed

- The default interactive command now opens the dashboard when attached to a terminal.
- The classic Rich report remains available through `devdoctor --classic` and all script/export modes remain compatible.

### Security

- Install, Auto Fix, and Optimization actions remain preview-only. DevDoctor does not execute package installation or cleanup commands automatically.
