# Release Readiness

Date: 2026-08-27  
Candidate: `1.2.0rc1`  
Repository: `imedkablavi/DevDoctor`  
Python distribution: `devdoctor-cli`  
Executable: `devdoctor`

## Current decision

**Do not tag `v1.2.0rc1` yet.**

The release-candidate code and release pipeline are prepared, but the final PR head must run through the complete GitHub Actions matrix before a tag is created. A passing workflow from an older commit is useful historical evidence, but it is not accepted as qualification for the current release commit.

This document intentionally contains no self-assigned percentage or readiness score. Release status is determined by reproducible checks and external publication state.

## Implemented in the candidate

- Python 3.11 through 3.14 CI matrix.
- Clean-wheel installation matrix.
- APT, DNF, rpm-ostree, Pacman, Zypper, Nix, Flatpak, and mixed-manager policy fixtures.
- Distro/container integration workflow for selected package managers.
- Fedora Atomic/Bazzite policy that suppresses DNF host mutation.
- Package-manager conflict and PATH ownership/version diagnostics.
- Privacy-scrubbed diagnostic export.
- Bash, Zsh, and Fish completion generation.
- Transaction-journaled repair application and rollback paths.
- Correct `devdoctor-cli` self-update target.
- Ownership-verified, fail-closed uninstall planning.
- Release tag/package-version consistency check.
- One-build release pipeline: tested artifacts are reused for GitHub Release and optional PyPI publication.
- SHA-256 release manifest.
- SPDX 2.3 SBOM generation.
- GitHub/Sigstore provenance and SBOM attestations.
- PyPI Trusted Publishing job gated by a repository variable and protected `pypi` environment.

## Required qualification gates

The exact commit that will be tagged must satisfy all of these gates.

### Source and package quality

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] Full `pytest` suite.
- [ ] Package build with `python -m build`.
- [ ] `twine check dist/*`.
- [ ] Project version equals package `__version__`.
- [ ] Console entry point resolves to `devdoctor.entrypoint:main`.

### Clean installation

- [ ] Wheel installs in a fresh Python 3.11 environment.
- [ ] Wheel installs in a fresh Python 3.12 environment.
- [ ] Wheel installs in a fresh Python 3.13 environment.
- [ ] Wheel installs in a fresh Python 3.14 environment.
- [ ] Installed `devdoctor --version` works.
- [ ] Installed completion generation works.
- [ ] Installed privacy diagnostics produce valid JSON.
- [ ] Installed `self-update` preview targets `devdoctor-cli`.

### Package-manager safety

- [ ] Fixture matrix passes.
- [ ] Ubuntu/APT integration passes.
- [ ] Fedora/DNF integration passes.
- [ ] Arch/Pacman integration passes.
- [ ] openSUSE/Zypper integration passes.
- [ ] Nix and Flatpak detection integration passes.
- [ ] Synthetic Fedora Atomic policy test passes without DNF host planning.
- [ ] Synthetic Bazzite policy test passes without DNF host planning.
- [ ] Ambiguous uninstall ownership fails closed.
- [ ] Atomic RPM ownership is not treated as proof of rpm-ostree layering.
- [ ] Repair rollback allowlist/invariant tests pass.

### Release artifacts

- [ ] Tag version matches package version.
- [ ] Wheel and sdist are generated once by the release build job.
- [ ] Clean-wheel validation uses the generated wheel.
- [ ] `devdoctor-install.sh` is added to the release payload.
- [ ] SPDX SBOM is generated successfully.
- [ ] `SHA256SUMS` verifies successfully.
- [ ] Provenance attestation succeeds.
- [ ] SBOM attestation succeeds.
- [ ] GitHub prerelease contains the expected payload.

## External setup gates

These cannot be proven by repository code alone.

### PyPI

Before setting `PYPI_TRUSTED_PUBLISHING_ENABLED=true`:

- [ ] Create or confirm the `devdoctor-cli` project/pending publisher on PyPI.
- [ ] Configure the trusted publisher for `imedkablavi/DevDoctor` and `.github/workflows/release.yml`.
- [ ] Configure the GitHub environment named `pypi`.
- [ ] Add the desired environment reviewer/protection policy.
- [ ] Confirm the tagged release workflow has `id-token: write` only where required.

The repository does not use a long-lived PyPI API token for this path.

### Stable-release repository protection

Before promoting the candidate to stable:

- [ ] Protect `main` with required CI/code-quality checks or an equivalent repository ruleset.
- [ ] Prevent direct merges that bypass release-critical checks.
- [ ] Prefer automatic deletion of merged feature branches.

### Homebrew

Homebrew is not a blocker for the release candidate. It must not be advertised as supported until:

- [ ] A real tap exists.
- [ ] Formula URLs and hashes reference immutable release artifacts.
- [ ] Formula installation passes in a clean Homebrew CI environment.

## Evidence policy

DevDoctor distinguishes:

- **Unit/fixture verified** — deterministic policy covered by tests.
- **Clean-wheel verified** — built package installs and starts in a new environment.
- **Host/container integration verified** — CI exercised a real distro/container package manager.
- **Manual workstation verified** — behavior was tested on an actual workstation/image.

Synthetic Fedora Atomic and Bazzite containers validate policy only. They are not evidence of real Bazzite workstation, desktop, hardware, reboot, or rpm-ostree deployment behavior.

## Promotion rule

`v1.2.0rc1` may be tagged only when the current commit's required automated gates are green.

`v1.2.0` stable requires the same gates plus review of release-candidate feedback and no unresolved high-severity regression in install, update, uninstall, repair, rollback, self-update, or package-manager selection.
