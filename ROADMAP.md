# Roadmap

DevDoctor is a Linux workstation bootstrap and repair CLI. The roadmap favors correctness, distro coverage, and safe local operation over broad automation.

## Near Term

- Add more verified package mappings for openSUSE, Void, Alpine, Nix, and language package managers.
- Expand repair checks for distro-specific package metadata and service managers.
- Add external plugin examples for private workstation catalogs.
- Improve snapshot tests for terminal output in narrow and wide terminals.
- Add package-manager dry-run parsers only where managers expose real dependency or download-size data.

## Later

- Signed release artifacts.
- PyPI trusted publishing workflow.
- More distro fixtures for install-plan selection.
- Optional machine-readable schema documentation for bootstrap JSON.
- More documentation for enterprise onboarding scripts.

## Non-goals

- A GUI or dashboard.
- Automatic privileged repair.
- Secret scanning or credential collection.
- Guessing latest versions from the network during local inventory.
- Support for non-Linux target systems.
