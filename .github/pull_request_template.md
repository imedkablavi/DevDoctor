## Summary

Describe the change and the user-visible impact.

## User Experience

- [ ] Terminal output remains readable in small terminals.
- [ ] Dashboard changes preserve keyboard-only navigation.
- [ ] No-color or classic script modes remain usable where applicable.

## Validation

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `pytest`
- [ ] `python -m devdoctor --classic --quiet --network-timeout 1`
- [ ] `python -m devdoctor --json --network-timeout 1 | python -m json.tool`

## Checklist

- [ ] Checks are isolated and cannot crash the full report.
- [ ] New warnings or failures include actionable recommendations.
- [ ] User-facing output is accurate and does not claim unsupported behavior.
- [ ] Install, Auto Fix, and cleanup actions do not execute automatically.
- [ ] Brand assets or UI colors follow `docs/BRAND.md`.
- [ ] Documentation is updated when behavior changes.
