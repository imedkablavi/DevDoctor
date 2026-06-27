# Checks Reference

Each check returns a typed `CheckResult` and is executed in isolation. Unexpected exceptions are converted into failed check results so a single probe cannot crash the full report.

Checks are registered through `CheckPlugin` metadata. The built-in registry preserves the original check order, and future third-party plugins can register through the `devdoctor.checks` entry point group.

## System

- Linux distribution: hostname, username, distro name, ID, ID-like family, version, support status, desktop/session hints, shell, terminal, primary package manager, battery, and temperature when available.
- Kernel: release, version, architecture, and Python platform string.
- CPU: model, logical cores, physical cores, current utilization, and load averages.
- RAM: total memory, available memory, utilization, swap capacity, and swap utilization.
- Disk: free, used, total, utilization, filesystem, device, and mountpoint for the user's home filesystem.
- Uptime: boot time and elapsed uptime.
- GPU: detected through `lspci` or `nvidia-smi` when available.

## Development Tools

DevDoctor checks command availability, executable path, version output, and selected runtime health where applicable.

- Git
- Docker
- Podman
- Python
- Node.js
- npm
- pnpm
- Bun
- Rust
- Cargo
- Go
- Java
- GitHub CLI
- kubectl
- Helm
- Terraform

Git and Python are treated as essential for the health score. Most other tools are warnings when missing because their importance depends on the user's project stack.

## Network

- Internet connectivity through outbound TCP probes.
- DNS resolution for GitHub, PyPI, and npm registry hosts.
- GitHub reachability over HTTPS.

## Scoring

Score starts at 100:

- Failed checks subtract `6 + weight * 4`.
- Warning checks subtract `weight * 2`.
- Checks with weight `0` are informational.

The score is clamped to the inclusive range `0..100`.
