# Migration Notes: v1.0.0

DevDoctor v1.0.0 keeps existing CLI behavior for automation while making the interactive dashboard the default terminal experience.

## What Changed

- Running `devdoctor` in an interactive terminal opens the Textual dashboard.
- The classic Rich report is available with `devdoctor --classic`.
- JSON, HTML, Markdown, PDF, quiet mode, fail-under, and save-latest options run as non-dashboard scan/export flows.

## Script Compatibility

No changes are required for scripts that use:

```bash
devdoctor --json
devdoctor --quiet
devdoctor --fail-under 80
devdoctor --json-file report.json
```

For human-readable non-dashboard output, use:

```bash
devdoctor --classic
```

## Plugin Authors

Future checks should register `CheckPlugin` metadata or expose a zero-argument check callable through the `devdoctor.checks` entry point group.

Each check must return a normalized `CheckResult` and must not require root privileges.

