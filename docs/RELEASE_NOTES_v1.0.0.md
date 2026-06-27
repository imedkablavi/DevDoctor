# DevDoctor v1.0.0 Release Notes

DevDoctor v1.0.0 is the first stable release of the Linux workstation diagnostics CLI.

## Highlights

- Interactive Textual dashboard with sidebar navigation, search, mouse support, and background scans.
- Health overview with score, pass/warning/failure counts, last scan, and recommendations.
- Tool cards with detailed pages for Git, Docker, Podman, Python, Node.js, npm, pnpm, Bun, Rust, Cargo, Go, Java, GitHub CLI, kubectl, Helm, and Terraform.
- System, networking, security, package manager, optimizer, Auto Fix, reports, settings, and about pages.
- JSON, HTML, Markdown, and compact PDF report export.
- Plugin registry for built-in and future external checks.
- Complete brand system with logo, icon, favicon, social banner, and animated preview.

## Compatibility

- `devdoctor` opens the dashboard in interactive terminals.
- `devdoctor --classic` preserves the original Rich report experience.
- `--json`, `--json-file`, `--html-file`, `--markdown-file`, `--pdf-file`, `--quiet`, and `--fail-under` remain script-friendly.

## Safety

DevDoctor does not run install, cleanup, or privileged commands automatically. Auto Fix and Optimization pages show the command and require explicit user action.

## Validation

Release validation should include:

```bash
ruff format --check .
ruff check .
pytest
python -m devdoctor --classic --quiet --network-timeout 1
python -m devdoctor --json --network-timeout 1 | python -m json.tool
python -m build
python -m twine check dist/*
```
