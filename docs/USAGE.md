# Usage

DevDoctor is designed to be useful both as an interactive terminal dashboard and in scripts.

## Interactive Scan

```bash
devdoctor
```

The default command opens the Textual dashboard when attached to an interactive terminal. It includes:

- System information
- Overall health score
- Permanent sidebar navigation
- Search
- Tool cards and detail pages
- Package-manager inventory
- Optimization and Auto Fix command previews
- JSON, HTML, Markdown, PDF, and clipboard report actions
- Recommendations

Use the classic Rich report explicitly:

```bash
devdoctor --classic
```

## JSON Output

```bash
devdoctor --json
```

This prints the complete report as JSON. Use this mode when piping output to tools.

```bash
devdoctor --json-file devdoctor-report.json
```

## HTML Output

```bash
devdoctor --html-file devdoctor-report.html
```

The HTML exporter creates a standalone report with embedded styles and raw JSON data.

## Markdown and PDF Output

```bash
devdoctor --markdown-file devdoctor-report.md
devdoctor --pdf-file devdoctor-report.pdf
```

Markdown is intended for issues, pull requests, and handoffs. The PDF exporter is dependency-free and produces a compact summary; use JSON, HTML, or Markdown for full raw data.

## Script Mode

```bash
devdoctor --quiet --fail-under 80
```

`--quiet` prints a compact summary:

```text
score=92 passed=22 warnings=4 failed=0
```

`--fail-under` exits with status code `1` when the score is below the threshold.

## Dashboard Shortcuts

- `/`: focus global search.
- `Tab`: switch to the next page.
- `Ctrl+R`: refresh checks in the background.
- `Ctrl+E`: open Reports.
- `Ctrl+F`: open Auto Fix.
- `Esc`: navigate back.
- `Q`: quit.

## Safety

Install, Auto Fix, and Optimization actions show the exact command. DevDoctor does not execute package installation or cleanup commands automatically.

## Accessibility

DevDoctor supports small and wide terminals through responsive dashboard card grids. Classic output supports no-color mode:

```bash
devdoctor --classic --no-color
```

See [ACCESSIBILITY.md](ACCESSIBILITY.md) for details.

## Network Timeout

```bash
devdoctor --network-timeout 5
```

The timeout applies to internet, DNS, and GitHub reachability checks.

## Latest Report Cache

```bash
devdoctor --save-latest
```

This writes the latest JSON report to the platformdirs user state directory. On most Linux systems that is `~/.local/state/devdoctor/`.

## Options

| Option | Use |
| --- | --- |
| `--version` | Print the installed DevDoctor version. |
| `--classic` | Use the Rich report instead of the dashboard. |
| `--json` | Print the full report as JSON. |
| `--json-file PATH` | Write a JSON report. |
| `--html-file PATH` | Write a standalone HTML report. |
| `--markdown-file PATH` | Write a Markdown report. |
| `--pdf-file PATH` | Write a compact PDF report. |
| `--save-latest` | Save the latest JSON report under the user state directory. |
| `--quiet`, `-q` | Print only the compact status line. |
| `--fail-under N` | Exit with code `1` when the score is below `N`. |
| `--network-timeout SECONDS` | Set the timeout for network probes. |
| `--no-progress` | Disable progress bars in classic output. |
| `--no-color` | Disable color in classic and script output. |
