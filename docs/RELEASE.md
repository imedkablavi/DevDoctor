# Release Process

This checklist is for maintainers cutting a DevDoctor release.

## Before Tagging

- Confirm `pyproject.toml` and `devdoctor/__init__.py` use the same version.
- Update `CHANGELOG.md`.
- Update `docs/RELEASE_NOTES_v1.0.0.md` or add notes for the new version.
- Check README commands, asset paths, and documentation links.
- Run validation from a clean checkout.

## Validation

```bash
ruff format --check .
ruff check .
pytest
python -m devdoctor --quiet
python -m devdoctor --json | python -m json.tool
python -m devdoctor check git --quiet
python -m devdoctor list profiles --no-color
python -m build
python -m twine check dist/*
```

## Publication

- Push the release branch and wait for CI.
- Create the GitHub release using `.github/RELEASE_TEMPLATE.md`.
- Publish the package to PyPI.
- Verify installation in a temporary virtual environment:

```bash
python -m venv /tmp/devdoctor-release-check
/tmp/devdoctor-release-check/bin/python -m pip install devdoctor
/tmp/devdoctor-release-check/bin/devdoctor --version
/tmp/devdoctor-release-check/bin/devdoctor --quiet
```

## After Publication

- Confirm badges render on GitHub.
- Confirm PyPI renders the README correctly.
- Open a clean terminal and run `devdoctor`, `devdoctor --json`, and `devdoctor list profiles`.
