# Release distribution readiness

## Release payload

A qualified tagged release is designed to build one release payload and reuse it for every publication destination:

- source distribution (`.tar.gz`)
- Python wheel (`.whl`)
- `devdoctor-install.sh`
- SPDX 2.3 SBOM (`devdoctor.spdx.json`)
- `SHA256SUMS`

The release workflow validates formatting, lint, tests, package metadata, and a clean wheel installation before the payload is uploaded.

The tag name is also checked against the package version. A tag such as `v1.2.0rc1` must point at code whose package version is exactly `1.2.0rc1`.

## Build once, publish the tested artifacts

The wheel and sdist are created in the release `build` job. That same job:

1. validates the built distributions,
2. installs the wheel into a new virtual environment,
3. runs CLI smoke checks,
4. creates the SBOM and checksum manifest,
5. creates provenance and SBOM attestations,
6. uploads the complete payload as a GitHub Actions artifact, and
7. creates the GitHub Release for tag-triggered runs.

The PyPI job downloads that exact Actions artifact. It does not rebuild the package.

## PyPI Trusted Publishing

The package name is `devdoctor-cli` and the console command is `devdoctor`.

PyPI publishing is intentionally disabled until external setup is complete. A tag-triggered release publishes to PyPI only when the repository variable below is set:

```text
PYPI_TRUSTED_PUBLISHING_ENABLED=true
```

Before enabling it:

1. Create or configure the `devdoctor-cli` project/pending publisher on PyPI.
2. Add a Trusted Publisher for `imedkablavi/DevDoctor`.
3. Set the workflow to `.github/workflows/release.yml`.
4. Set the GitHub environment name to `pypi`.
5. Create/protect the `pypi` environment in GitHub with the desired reviewer policy.
6. Run the release workflow without a publication-enabled tag and inspect the generated package artifacts.
7. Enable the repository variable only when the external publisher configuration is correct.

Do not add a long-lived PyPI API token for this release path.

## Install script

`scripts/install.sh` performs a user-space installation using a dedicated virtual environment. It does not invoke `sudo` and refuses a non-interactive install unless `--yes` is explicitly supplied.

For a downloaded release asset:

```sh
sh devdoctor-install.sh
```

For automation where the caller has already approved the change:

```sh
sh devdoctor-install.sh --yes
```

A release candidate can be pinned explicitly:

```sh
sh devdoctor-install.sh --version 1.2.0rc1
```

The script installs versioned environments under the user data directory and repoints the command symlink only after a successful install. Previous version directories are retained for manual rollback.

## Checksums

Release consumers can verify the local payload with:

```sh
sha256sum --check SHA256SUMS
```

`SHA256SUMS` is generated from a sorted list of release files and does not include itself.

A checksum manifest proves byte integrity relative to the manifest. It does not by itself prove who produced the artifact.

## Provenance and SBOM attestations

The public release workflow uses `actions/attest` with GitHub OIDC to create keyless attestations for the release payload.

The workflow creates:

- build provenance for the release artifact checksums, and
- an SBOM attestation that binds `devdoctor.spdx.json` to the wheel and sdist.

For a downloaded release artifact, GitHub CLI can be used to verify a repository attestation:

```sh
gh attestation verify devdoctor_cli-1.2.0rc1-py3-none-any.whl \
  --repo imedkablavi/DevDoctor
```

The SPDX file describes the DevDoctor distribution and its declared direct runtime dependencies. It is generated deterministically from package metadata and release artifact hashes; it does not claim to be a full operating-system or transitive dependency inventory.

## Homebrew readiness

The repository contains a formula readiness template, not a published Homebrew distribution channel.

Do not advertise `brew install ...` until all of the following are true:

- a real tap repository exists,
- release URLs are immutable,
- SHA-256 hashes match the final tagged artifacts,
- Python resources are handled correctly for the formula strategy, and
- a clean Homebrew CI job installs and runs `devdoctor --version` successfully.

## Release candidate policy

`v1.2.0rc1` is a prerelease. GitHub Release is configured to mark tags containing `rc` as prereleases.

Promotion to a stable `v1.2.0` requires the current commit's full CI/release qualification, review of release-candidate feedback, and no unresolved high-severity mutation or package-manager-selection regression.
