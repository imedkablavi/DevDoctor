# CLI Reference

This reference covers DevDoctor commands as implemented by the Typer CLI. Use `devdoctor --help` and `devdoctor COMMAND --help` for the exact option list installed on your system.

## `devdoctor`

Runs the default bootstrap inventory.

```bash
devdoctor
devdoctor --quiet
devdoctor --json
devdoctor --json-file inventory.json
devdoctor --markdown-file inventory.md
devdoctor --html-file inventory.html
```

Exit code: `0` unless argument parsing fails.

Related commands: `check`, `export`, `health`.

## `devdoctor check`

Inspects selected tools, a profile, or a category.

```bash
devdoctor check git docker node
devdoctor check --profile devops
devdoctor check --category containers
devdoctor check --missing
devdoctor check --json
```

Exit code: `0` unless argument parsing fails or an unknown profile, category, or tool ID is requested.

Related commands: `verify`, `install`, `repair`.

## `devdoctor doctor`

Alias for a full bootstrap check.

```bash
devdoctor doctor
devdoctor doctor git docker
devdoctor doctor --profile backend
```

Exit code: `0` unless argument parsing fails.

Related command: `check`.

## `devdoctor verify`

Checks selected tools and exits non-zero if any selected tool is missing, warning, or broken.

```bash
devdoctor verify --profile general
devdoctor verify git python docker --quiet
```

Exit code: `0` when selected tools are ready. Exit code: `1` when selected tools are not ready.

Related commands: `check`, `install`, `repair`.

## `devdoctor profiles`

Lists built-in profiles.

```bash
devdoctor profiles
devdoctor profiles --json
```

Exit code: `0`.

Related command: `list profiles`.

## `devdoctor search`

Searches the local bootstrap catalog.

```bash
devdoctor search docker
devdoctor search python
```

Exit code: `0` when matches exist. Exit code: `1` when no catalog entries match.

Related commands: `list tools`, `check`.

## `devdoctor install`

Previews or executes safe install plans for missing tools.

```bash
devdoctor install git docker
devdoctor install git docker --dry-run
devdoctor install --profile frontend --dry-run
devdoctor install --profile frontend --apply
```

Exit code: `0` when plans are printed or commands complete. A failed executed command exits with that command's exit code.

Notes:

- No package install runs unless `--apply` or `--dry-run` is passed.
- `--dry-run` runs package-manager simulation commands when available.
- `--yes` skips confirmation prompts and should only be used in controlled scripts.

Related commands: `check`, `verify`, `uninstall`.

## `devdoctor repair`

Shows read-only repair suggestions for selected tools.

```bash
devdoctor repair
devdoctor repair docker
devdoctor repair --profile flutter
```

Exit code: `0`. Repair suggestions are not executed by this command.

Related commands: `check`, `install`, `verify`.

## `devdoctor uninstall`

Previews or executes rollback commands for catalog tools where a rollback command is known.

```bash
devdoctor uninstall docker
devdoctor uninstall docker --apply
```

Exit code: `0` when rollback plans are printed or commands complete. Exit code: `1` when no rollback command is available for the selected tools.

Related commands: `install`, `update`.

## `devdoctor update`

Previews or runs update commands for detected package managers.

```bash
devdoctor update
devdoctor update --apply
```

Exit code: `0` when commands are printed or complete. Exit code: `1` when no supported package manager update command is detected.

Related commands: `cache clean`, `self-update`.

## `devdoctor self-update`

Previews or runs a Python package self-update.

```bash
devdoctor self-update
devdoctor self-update --apply
```

Exit code: `0` when the command is printed or completes.

Related command: `update`.

## `devdoctor export`

Exports bootstrap inventory as JSON or Markdown.

```bash
devdoctor export json
devdoctor export json --output inventory.json
devdoctor export markdown --output inventory.md
```

Exit code: `0` for supported formats. Exit code: `2` for unsupported export formats.

Related commands: `devdoctor --json`, `devdoctor --markdown-file`.

## `devdoctor list`

Lists catalog data.

```bash
devdoctor list profiles
devdoctor list tools
devdoctor list tools --category terminal-utilities
devdoctor list categories
```

Exit code: `0` unless an unknown category is requested.

Related commands: `profiles`, `search`.

## `devdoctor cache clean`

Previews or runs supported package-cache cleanup commands.

```bash
devdoctor cache clean
devdoctor cache clean --apply
```

Exit code: `0`.

Related command: `update`.

## `devdoctor health`

Runs the legacy non-interactive health report.

```bash
devdoctor health
devdoctor health --quiet
devdoctor health --json
devdoctor health --html-file health.html
devdoctor health --pdf-file health.pdf
devdoctor health --quiet --fail-under 80
```

Exit code: `0` unless `--fail-under` is set and the legacy score is below the threshold.

Related command: `devdoctor`.
