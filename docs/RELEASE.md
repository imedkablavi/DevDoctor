# Release Process

This checklist is for maintainers cutting a DevDoctor release.

## Before Tagging

- Confirm `pyproject.toml` and `devdoctor/__init__.py` use the same version.
- Confirm the Python distribution name is `devdoctor-cli`.
- Confirm the executable entry point remains `devdoctor`.
- Update `CHANGELOG.md`.
- Update the release notes for the new version.
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
python -m devdoctor search docker --no-color
python -m devdoctor repair docker --no-color
python -m devdoctor list profiles --no-color
python -m build
python -m twine check dist/*
```

Before the first PyPI upload, confirm whether the distribution name is already published:

```bash
python -m pip index versions devdoctor-cli || true
```

## Publication

- Push the release branch and wait for CI.
- Create the GitHub release using `.github/RELEASE_TEMPLATE.md`.
- Publish the `devdoctor-cli` package to PyPI.
- Verify installation in a temporary virtual environment:

```bash
python -m venv /tmp/devdoctor-release-check
/tmp/devdoctor-release-check/bin/python -m pip install devdoctor-cli
/tmp/devdoctor-release-check/bin/devdoctor --version
/tmp/devdoctor-release-check/bin/devdoctor --quiet
```

Future Homebrew tap command, after the tap is implemented:

```bash
brew install imedkablavi/tap/devdoctor
```

## After Publication

- Confirm badges render on GitHub.
- Confirm PyPI renders the README correctly.
- Open a clean terminal and run `devdoctor`, `devdoctor --json`, `devdoctor search docker`, and `devdoctor list profiles`.
