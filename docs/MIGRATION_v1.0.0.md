# Migration Notes: v1.0.0

DevDoctor v1.0.0 changes the default product model from workstation health reporting to workstation bootstrap inventory.

## What Changed

- `devdoctor` prints a bootstrap inventory instead of launching a dashboard.
- `devdoctor --json` returns bootstrap inventory JSON.
- `devdoctor --quiet` prints installed, missing, broken, and total counts.
- Install, update, uninstall, cache-clean, and self-update commands preview operations and require `--apply` to execute.
- The Textual dashboard is no longer part of the package.

## Health Report Compatibility

Use `devdoctor health` for the legacy health report model:

```bash
devdoctor health
devdoctor health --json
devdoctor health --quiet --fail-under 80
devdoctor health --html-file health.html
devdoctor health --pdf-file health.pdf
```

## Script Migration

Old:

```bash
devdoctor --quiet --fail-under 80
```

New:

```bash
devdoctor verify --profile general --quiet
```

Old:

```bash
devdoctor --json > report.json
```

New bootstrap JSON:

```bash
devdoctor --json > inventory.json
```

Legacy health JSON:

```bash
devdoctor health --json > health.json
```

## Plugin Authors

Bootstrap catalog plugins should register `ToolSpec` providers through `devdoctor.bootstrap_tools`.

Legacy health-check plugins can continue using the `devdoctor.checks` entry point group.
