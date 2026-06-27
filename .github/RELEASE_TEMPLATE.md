# DevDoctor v1.0.0

## Highlights

- Interactive Textual dashboard with sidebar navigation, search, keyboard shortcuts, and background scans.
- Linux workstation checks for system health, developer tools, containers, DNS, internet, and GitHub reachability.
- Safe Auto Fix and Optimization pages that show exact commands without executing them.
- JSON, HTML, Markdown, compact PDF, clipboard, and latest-report export workflows.
- v1 brand system with logo, icon, favicon, GitHub banner, and terminal preview.

## Installation

```bash
python -m pip install --upgrade devdoctor
```

## Compatibility

- Dashboard: `devdoctor`
- Classic report: `devdoctor --classic`
- JSON: `devdoctor --json`
- CI gate: `devdoctor --quiet --fail-under 75`

## Validation

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `pytest`
- [ ] `python -m devdoctor --classic --quiet --network-timeout 1`
- [ ] `python -m devdoctor --classic --no-color --quiet --network-timeout 1`
- [ ] `python -m devdoctor --json --network-timeout 1 | python -m json.tool`
- [ ] `python -m build`
- [ ] `python -m twine check dist/*`

## Security Notes

DevDoctor does not execute install, Auto Fix, or cleanup commands automatically.
