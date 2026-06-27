# Release Process

This checklist is for maintainers cutting a DevDoctor release.

## Before Tagging

- Confirm `pyproject.toml` and `devdoctor/__init__.py` use the same version.
- Update `CHANGELOG.md`.
- Update `docs/RELEASE_NOTES_v1.0.0.md` or add notes for the new version.
- Check that README commands, asset paths, and documentation links still resolve.
- Run the validation commands below from a clean checkout.

## Validation

```bash
ruff format --check .
ruff check .
pytest
python -m devdoctor --classic --quiet --network-timeout 1
python -m devdoctor --json --network-timeout 1 | python -m json.tool
python -m build
```

For PyPI metadata validation:

```bash
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
```

## After Publication

- Confirm badges render on GitHub.
- Confirm PyPI shows the README correctly.
- Open a clean terminal and run `devdoctor`, `devdoctor --classic`, and `devdoctor --json`.
