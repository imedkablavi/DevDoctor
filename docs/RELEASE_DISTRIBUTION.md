# Release distribution readiness

## Release payload

A tagged release builds:

- source distribution (`.tar.gz`)
- Python wheel (`.whl`)
- `devdoctor-install.sh`
- `SHA256SUMS`

The release workflow verifies the wheel in a clean virtual environment before publishing GitHub release assets.

## PyPI

The package name is `devdoctor-cli` and the console command is `devdoctor`.

The release workflow contains an opt-in `publish-pypi` job using PyPI Trusted Publishing (OIDC). It runs only when a maintainer manually dispatches the release workflow with `publish_pypi=true`.

Before enabling it for a real release:

1. Configure a PyPI project named `devdoctor-cli`.
2. Add a Trusted Publisher for this GitHub repository, workflow `release.yml`, and environment `pypi`.
3. Protect the GitHub `pypi` environment with the desired reviewer policy.
4. Run the release workflow without publishing first and inspect the wheel, sdist, and checksums.
5. Only then dispatch with `publish_pypi=true`.

Do not add a long-lived PyPI API token to the repository.

## Install script

`scripts/install.sh` performs a user-space installation using a dedicated virtual environment. It never invokes `sudo` and refuses a non-interactive install unless `--yes` is explicitly supplied.

For release assets:

```sh
sh devdoctor-install.sh
```

For automation where the caller already approved the change:

```sh
sh devdoctor-install.sh --yes
```

A specific version can be pinned:

```sh
sh devdoctor-install.sh --version 1.1.0
```

The script installs versioned environments under the user data directory and only repoints the command symlink after a successful install. Previous version directories are retained for manual rollback.

## Homebrew readiness

Do not publish a Homebrew formula that downloads dependencies during the build. A production formula needs immutable release URLs and SHA-256 hashes for DevDoctor and its Python resources, or a maintained tap strategy that vendors those resources correctly.

The repository is considered **Homebrew-ready at the release-process level**, not published to Homebrew, when:

- a tagged sdist exists,
- `SHA256SUMS` is generated,
- PyPI metadata is valid,
- the formula template can be populated with immutable hashes,
- a tap CI job installs the formula in a clean Homebrew environment.

Until that final tap CI exists, documentation must not claim that `brew install devdoctor` is supported.

## Checksums

Release consumers can verify artifacts with:

```sh
sha256sum --check SHA256SUMS
```

Checksums prove integrity against the published checksum manifest. They are not a substitute for artifact signing or provenance. Signing/provenance should be added only after the release identity and keyless-signing policy are defined and tested.
