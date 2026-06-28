# Release Process

This is the public release checklist for DevDoctor maintainers.

## Prepare

1. Confirm `pyproject.toml` and `devdoctor/__init__.py` contain the same version.
2. Update `CHANGELOG.md`.
3. Add release notes under `docs/`.
4. Review README commands, screenshots, badges, and links.
5. Confirm issue templates, labels, and release template still match the project.

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

## Fresh Environment Check

```bash
python -m venv /tmp/devdoctor-release-check
/tmp/devdoctor-release-check/bin/python -m pip install dist/devdoctor-*.whl
/tmp/devdoctor-release-check/bin/devdoctor --version
/tmp/devdoctor-release-check/bin/devdoctor --quiet
```

## Publish

1. Push the release commit and wait for CI.
2. Create a signed tag when possible.
3. Push the tag.
4. Attach the wheel and source distribution from `dist/` to the GitHub release.
5. Publish to PyPI after `twine check` passes.
6. Verify installation from PyPI in a clean virtual environment.
