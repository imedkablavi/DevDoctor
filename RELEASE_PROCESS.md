# Release Process

This is the public release checklist for DevDoctor maintainers.

## Prepare

1. Confirm `pyproject.toml` and `devdoctor/__init__.py` contain the same version.
2. Confirm `pyproject.toml` uses distribution name `devdoctor-cli`.
3. Confirm `[project.scripts]` still exposes `devdoctor`.
4. Update `CHANGELOG.md`.
5. Add release notes under `docs/`.
6. Review README commands, screenshots, badges, and links.
7. Confirm issue templates, labels, and release template still match the project.

## Validate

```bash
ruff format --check .
ruff check .
pytest
python -m devdoctor --version
python -m devdoctor --quiet
python -m devdoctor --json | python -m json.tool
python -m devdoctor search docker --no-color
python -m devdoctor repair docker --no-color
python -m build
python -m twine check dist/*
```

Before the first PyPI upload, this command is expected to report no matching distribution:

```bash
python -m pip index versions devdoctor-cli || true
```

## Fresh Environment Check

```bash
python -m venv /tmp/devdoctor-release-check
/tmp/devdoctor-release-check/bin/python -m pip install --find-links dist devdoctor-cli
/tmp/devdoctor-release-check/bin/devdoctor --version
/tmp/devdoctor-release-check/bin/devdoctor --quiet
```

## Publish

1. Push the release commit and wait for CI.
2. Create a signed tag when possible.
3. Push the tag.
4. Attach the `devdoctor_cli-<version>` wheel and source distribution from `dist/` to the GitHub release.
5. Publish `devdoctor-cli` to PyPI after `twine check` passes.
6. Verify installation from PyPI in a clean virtual environment:

```bash
python -m venv /tmp/devdoctor-pypi-check
/tmp/devdoctor-pypi-check/bin/python -m pip install devdoctor-cli
/tmp/devdoctor-pypi-check/bin/devdoctor --version
```

## Future Homebrew Tap

The tap is not implemented yet. When it exists, the intended install command is:

```bash
brew install imedkablavi/tap/devdoctor
```
