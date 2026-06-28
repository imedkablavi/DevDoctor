# DevDoctor v1.1.0 Release Notes

DevDoctor v1.1.0 turns the bootstrap inventory into an intelligent detection and repair engine while keeping the CLI read-only by default.

## Highlights

- Tool health states: `ready`, `missing`, `warning`, and `broken`.
- Dependency-aware checks for Docker, Flutter, Git, Python, Node.js, Java, Cargo, kubectl, and related toolchains.
- Repair recommendations with problem, reason, risk, command or manual action, verification command, and rollback command when known.
- PATH analysis for duplicate entries, missing directories, unexported user binary directories, broken executable symlinks, and shadowed commands.
- Search results now include category, health, version, installation method, profiles, dependencies, install command, and website.
- Install plans explain why a package manager was selected and whether sudo is required.
- Executed operations are logged as JSON Lines with command results and verification results.

## Compatibility

The public CLI shape remains compatible with v1.0.0:

```bash
devdoctor
devdoctor check --profile devops
devdoctor install git docker --dry-run
devdoctor repair docker
devdoctor search docker
devdoctor export json --output inventory.json
```

The legacy health report remains available through `devdoctor health`.

## Safety

Inventory, search, and repair commands do not modify the system. Commands that change packages, caches, or DevDoctor itself still require `--apply`, and each command asks for confirmation unless `--yes` is provided.

Repair recommendations are intentionally conservative. DevDoctor prints shell exports, service commands, and manual actions, but it does not edit shell startup files, start services, change group membership, or remove packages from the `repair` command.

## Upgrade

```bash
python -m pip install --upgrade devdoctor
devdoctor --version
devdoctor check --profile general
```

## Validation

This release was prepared with:

```bash
ruff format --check .
ruff check .
pytest
python -m devdoctor --quiet
python -m devdoctor --json | python -m json.tool
python -m build
python -m twine check dist/*
```
