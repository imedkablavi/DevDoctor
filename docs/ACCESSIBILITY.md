# Accessibility

DevDoctor is designed for plain terminal use, non-interactive shells, tmux sessions, and CI logs.

## Terminal Sizes

- Narrow terminals receive folded command and path columns.
- Wide terminals show host context, category tables, and install plans with more breathing room.
- Machine-readable output should use `--json` or `export json`.
- Script output should use `--quiet`.

## Color

Rich chooses the best available color mode automatically.

```bash
devdoctor --no-color
devdoctor check --profile devops --no-color
```

`--no-color` is supported by the default command and primary subcommands.

## Unicode

Terminal output uses a small set of status symbols:

- `✓` installed
- `✗` missing
- `!` warning or broken state that needs review

Use JSON output when symbols are not appropriate for the consuming environment.

## Keyboard and Interaction

DevDoctor does not require a mouse. Commands that can change the system use terminal confirmation prompts unless `--yes` is provided explicitly.

## Reduced Risk

Inventory commands are read-only. Install, update, uninstall, cache-clean, and self-update operations require `--apply`.
