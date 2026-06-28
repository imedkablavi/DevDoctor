# DevDoctor v1.1.0

## Highlights

- Intelligent Linux workstation inventory with health states.
- Dependency-aware detection and repair recommendations.
- PATH analysis for missing, duplicate, unexported, and shadowed command paths.
- Distro-aware install, update, uninstall, repair, and cache-clean command planning.
- Built-in profiles for common developer roles.
- JSON, Markdown, and standalone HTML inventory exports.
- Structured operation logging with verification results.
- Bootstrap catalog plugin entry point group.

## Installation

```bash
python -m pip install --upgrade devdoctor
```

## Compatibility

- Inventory: `devdoctor`
- JSON: `devdoctor --json`
- Profiles: `devdoctor list profiles`
- Search: `devdoctor search docker`
- Repair suggestions: `devdoctor repair docker`
- Legacy health reports: `devdoctor health`

## Validation

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `pytest`
- [ ] `python -m devdoctor --version`
- [ ] `python -m devdoctor --quiet`
- [ ] `python -m devdoctor --no-color --quiet`
- [ ] `python -m devdoctor --json | python -m json.tool`
- [ ] `python -m devdoctor search docker --no-color`
- [ ] `python -m devdoctor repair docker --no-color`
- [ ] `python -m devdoctor list profiles --no-color`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`

## Security Notes

DevDoctor does not execute install, update, uninstall, cache, or self-update commands without `--apply`.

## Artifacts

- Source distribution: `devdoctor-<version>.tar.gz`
- Wheel: `devdoctor-<version>-py3-none-any.whl`

Run `python -m twine check dist/*` before publishing artifacts.
