# DevDoctor v1.0.0

## Highlights

- Bootstrap-first Linux workstation inventory.
- Distro-aware install, update, uninstall, repair, and cache-clean command planning.
- Built-in profiles for common developer roles.
- JSON, Markdown, and standalone HTML inventory exports.
- Bootstrap catalog plugin entry point group.
- v1 brand system with logo, icon, favicon, and GitHub banner.

## Installation

```bash
python -m pip install --upgrade devdoctor
```

## Compatibility

- Inventory: `devdoctor`
- JSON: `devdoctor --json`
- Profiles: `devdoctor list profiles`
- Legacy health reports: `devdoctor health`

## Validation

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `pytest`
- [ ] `python -m devdoctor --quiet`
- [ ] `python -m devdoctor --no-color --quiet`
- [ ] `python -m devdoctor --json | python -m json.tool`
- [ ] `python -m devdoctor list profiles --no-color`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`

## Security Notes

DevDoctor does not execute install, update, uninstall, cache, or self-update commands without `--apply`.
