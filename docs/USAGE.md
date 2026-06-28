# Usage

DevDoctor is a Linux workstation bootstrap CLI. The default command prints a local inventory and install plans; it does not open a dashboard and it does not calculate a health score.

For exhaustive command details, see [CLI Reference](CLI_REFERENCE.md). For copyable workflows, see [Examples](../examples/README.md).

## Inventory

```bash
devdoctor
devdoctor check
devdoctor check git docker node
devdoctor check --profile devops
devdoctor check --category cloud-clis
devdoctor check --missing
```

`--quiet` prints a compact summary for scripts:

```bash
devdoctor --quiet
```

```text
installed=33 missing=31 warnings=2 broken=0 total=64
```

Inventory rows include each tool's health state. `ready` means the command was found and no local problem was detected. `missing` means no usable executable was found. `warning` means the tool is present but has a repairable configuration, dependency, daemon, or PATH concern. `broken` is reserved for unusable local commands such as broken symlinks or bad executable permissions.

## JSON, Markdown, and HTML

```bash
devdoctor --json
devdoctor --json-file inventory.json
devdoctor --markdown-file inventory.md
devdoctor --html-file inventory.html
devdoctor export json --output inventory.json
devdoctor export markdown --output inventory.md
```

Raw JSON is written directly to stdout, so it is safe to pipe:

```bash
devdoctor --json | python -m json.tool
```

## Profiles

```bash
devdoctor list profiles
devdoctor profiles
devdoctor profiles --json
```

Use profiles to focus the catalog:

```bash
devdoctor check --profile python
devdoctor install --profile frontend --dry-run
devdoctor verify --profile general --quiet
```

## Install Plans

By default, `install` previews missing tools and prints package-manager commands without changing the system:

```bash
devdoctor install git docker
devdoctor install --profile devops
```

Run package-manager dry-run commands where supported:

```bash
devdoctor install git docker --dry-run
```

Execute a plan only after review:

```bash
devdoctor install git docker --apply
```

Use `--yes` only in controlled scripts:

```bash
devdoctor install --profile general --apply --yes
```

## Repair and Verification

```bash
devdoctor repair
devdoctor repair docker
devdoctor verify --profile general
devdoctor verify git python docker --quiet
```

`verify` exits with status code `1` when any selected tool is missing, warning, or broken.

Repair suggestions are derived from local evidence such as broken symlinks, non-executable files in `PATH`, missing dependencies, and package-manager ownership data when available.

Repair output includes the problem, why it matters, risk level, repair command or manual action, and a verification command when the catalog knows one. `repair` is read-only; it does not execute the suggested command.

Examples of checks DevDoctor can explain:

- Docker CLI installed but `docker info` cannot reach a daemon.
- Docker socket permission failures.
- Git missing global `user.name` or `user.email`.
- Missing SSH public key.
- Python installed without working `pip`.
- Node.js installed without `npm`.
- Java installed without `JAVA_HOME`.
- Cargo user binary directory missing from `PATH`.
- Flutter with missing Android toolchain dependencies.

## Catalog Search and Lists

```bash
devdoctor search kubectl
devdoctor search docker
devdoctor list tools
devdoctor list tools --category terminal-utilities
devdoctor list categories
```

Search output includes description, category, health state, installed version, installation method, profiles that reference the tool, dependency status, install command, and website. Tool IDs are stable command identifiers used by profiles and install plans.

When a selected tool declares required dependencies, DevDoctor includes those dependency tools in the inventory context. For example, `devdoctor check flutter` also evaluates Git, Java, ADB, and Android SDK command-line tools where the catalog knows the relationship. Search output can include optional dependency context as well.

## PATH Analysis

The default inventory shows a PATH panel when DevDoctor detects a problem. It can report:

- empty PATH entries
- duplicate directories
- missing directories
- entries that are files instead of directories
- directories that exist but are not searchable
- common user binary directories that exist but are not exported
- commands shadowed by another executable earlier in PATH

DevDoctor prints exact export commands only when it can infer them safely. It never edits shell startup files automatically.

## Update, Uninstall, and Cache Commands

These commands preview real package-manager operations. They execute only with `--apply`.

```bash
devdoctor update
devdoctor update --apply

devdoctor uninstall docker
devdoctor uninstall docker --apply

devdoctor cache clean
devdoctor cache clean --apply

devdoctor self-update
devdoctor self-update --apply
```

All executed commands are run with `shell=False` and are logged as JSON Lines to the platformdirs user state directory, usually `~/.local/state/devdoctor/operations.log`. For install and uninstall plans, DevDoctor also records the verification command and result when the catalog defines one.

## No Color

```bash
devdoctor --no-color
devdoctor check --profile devops --no-color
```

No-color mode is useful in simple terminals, logs, and CI systems.

## Legacy Health Report

The old non-interactive health report remains available for users that need the previous check/export model:

```bash
devdoctor health
devdoctor health --json
devdoctor health --json-file health.json
devdoctor health --html-file health.html
devdoctor health --markdown-file health.md
devdoctor health --pdf-file health.pdf
devdoctor health --quiet --fail-under 80
```

The legacy command is not the default product workflow.
