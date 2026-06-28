# Migration Guide

This page points to version-specific migration notes.

## v1.1.0

DevDoctor v1.1.0 keeps the v1.0 CLI shape and adds richer detection data:

- health states: `ready`, `missing`, `warning`, `broken`
- dependency status
- repair recommendations
- PATH analysis
- structured operation logs

Script users should note that `devdoctor --quiet` now includes a `warnings=` field:

```text
installed=33 missing=31 warnings=2 broken=0 total=64
```

Use `devdoctor --json` for a stable machine-readable inventory.

## v1.0.0

See [docs/MIGRATION_v1.0.0.md](docs/MIGRATION_v1.0.0.md).
