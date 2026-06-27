# Accessibility

DevDoctor is designed for keyboard-first terminal use across common Linux terminals, tmux sessions, and non-interactive shells.

## Terminal Sizes

- Small terminals use single-column dashboard card grids.
- Medium terminals use two-column card grids.
- Wide terminals use three-column card grids where the content benefits from it.
- Non-interactive shells can use `--classic`, `--quiet`, `--json`, or file export options.

## Color

- The dashboard uses Textual's terminal color negotiation.
- The classic Rich report uses Rich's automatic color detection.
- `--no-color` disables color for classic and script output:

```bash
devdoctor --classic --no-color
```

## Keyboard

Every primary dashboard workflow is reachable from the keyboard. The shortcut map is listed in [DASHBOARD.md](DASHBOARD.md).

## Reduced Risk

Install and cleanup workflows are preview-only. DevDoctor never automatically runs privileged or destructive commands.
