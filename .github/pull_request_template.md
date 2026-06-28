## Summary

Describe the change and the user-visible impact.

## Scope

- [ ] Bug fix
- [ ] Documentation
- [ ] Catalog/package mapping
- [ ] Repair or PATH analysis
- [ ] Packaging/release
- [ ] Other:

## User Experience

- [ ] Terminal output remains readable in small terminals.
- [ ] No-color and quiet modes remain usable where applicable.
- [ ] Machine-readable output is not routed through Rich formatting.

## Validation

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `pytest`
- [ ] `python -m devdoctor --quiet`
- [ ] `python -m devdoctor --json | python -m json.tool`
- [ ] `python -m devdoctor search docker --no-color`
- [ ] `python -m devdoctor repair docker --no-color`
- [ ] `python -m devdoctor list profiles --no-color`

## Security

- [ ] No new `shell=True` usage.
- [ ] No scan command mutates the system.
- [ ] Mutating commands still require `--apply`.
- [ ] Logs do not include secrets or unbounded command output.

## Checklist

- [ ] Probes are isolated and cannot crash the full inventory.
- [ ] New missing or broken states include actionable commands or repair text.
- [ ] User-facing output is accurate and does not claim unsupported behavior.
- [ ] System-changing actions require `--apply`.
- [ ] Brand assets or UI colors follow `docs/BRAND.md`.
- [ ] Documentation is updated when behavior changes.
