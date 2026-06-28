# DevDoctor v1.0.0 Release Notes

DevDoctor v1.0.0 is the first stable release of the Linux developer workstation bootstrap CLI.

## Highlights

- Bootstrap-first default command with no dashboard and no health score.
- Local host detection for Linux distribution, desktop/session, shell, terminal, architecture, virtualization, WSL, containers, sudo, PATH, and package managers.
- Catalog detection for 60+ developer tools across languages, containers, DevOps, cloud CLIs, databases, security, debugging, build systems, mobile, AI, and terminal utilities.
- Distro-aware install plans for APT, DNF, rpm-ostree, Pacman, Zypper, XBPS, APK, Nix, Homebrew, Flatpak, Snap, and language package managers.
- Profiles for general development, frontend, backend, Python, Node, Rust, Go, Java, Flutter, Android, data science, AI, security, DevOps, cloud, and game development.
- JSON, Markdown, and standalone HTML bootstrap exports.
- Confirmed execution flow for install, update, uninstall, cache-clean, and self-update commands.
- Bootstrap catalog plugin entry point group: `devdoctor.bootstrap_tools`.
- Legacy `devdoctor health` command for the older non-interactive health report exporters.

## Compatibility

- `devdoctor` now prints the bootstrap inventory.
- `devdoctor --json` now prints bootstrap inventory JSON.
- Previous health-style reports are available through `devdoctor health`.
- The Textual dashboard has been removed from the public CLI and package dependencies.

## Safety

Inventory commands are read-only. Commands that change the system require `--apply`, use `shell=False`, and are logged under the user state directory.

## Validation

```bash
ruff format --check .
ruff check .
pytest
python -m devdoctor --quiet
python -m devdoctor --json | python -m json.tool
python -m devdoctor list profiles --no-color
python -m build
python -m twine check dist/*
```
