# Distribution and package-manager support

DevDoctor separates **detection support**, **planning support**, and **environment-tested support**. A package manager being detectable does not mean DevDoctor is allowed to mutate the host with it.

## Safety contract

- DevDoctor previews install/update/uninstall commands before execution.
- Privileged commands are never run automatically.
- `--apply` is required for mutations and interactive confirmation remains the default.
- `--yes` only suppresses confirmation when the user explicitly supplied it.
- Fedora Atomic/Bazzite hosts never use `dnf` for host mutation. User-space managers are preferred; `rpm-ostree` layering is the system fallback.
- Flatpak is treated as a desktop application manager, not a generic replacement for host development packages.
- Nix is treated as a user/profile package manager unless a future feature explicitly models NixOS system configuration.

## Debian / Ubuntu / Linux Mint / Pop!_OS

Native host manager: **APT**.

DevDoctor can detect APT, generate mapped install plans, preview install operations, and generate rollback commands where the catalog supports them. Third-party repositories remain a manual responsibility.

Fixture coverage: `ubuntu-apt`.

## Fedora Workstation / mutable Fedora

Native host manager: **DNF**.

DNF install/update plans are allowed only when the host is not identified as Atomic/image-based.

Fixture coverage: `fedora-dnf`.

## Fedora Atomic desktops

Examples include Silverblue, Kinoite, Sericea/Sway Atomic, Onyx/Budgie Atomic, and other variants carrying Atomic/OSTree release metadata.

Host manager: **rpm-ostree**. DevDoctor suppresses DNF host mutation even if a `dnf` executable exists. The preference is user-space tooling first, then rpm-ostree layering when a catalog mapping exists. Layering can require a reboot.

Fixture coverage: `fedora-silverblue-rpm-ostree`.

## Bazzite / Universal Blue derivatives

Bazzite is treated as image-based. DevDoctor prefers **Homebrew** for mapped developer tools, then **rpm-ostree** when layering is the available mapped option. DNF is never selected for host mutation.

Fixture coverage: `bazzite-mixed`.

## Arch Linux / Manjaro

Native host manager: **Pacman**. `yay` and `paru` can be detected as optional community package managers, but native Pacman mappings take precedence when available.

Fixture coverage: `arch-pacman`.

## openSUSE Tumbleweed / Leap / SLES-like systems

Native host manager: **Zypper**. DevDoctor has explicit package mappings for the core developer-tool set covered by package-manager tests.

Fixture coverage: `opensuse-zypper`.

## Nix / Nix profiles

DevDoctor detects **Nix** and can generate user-profile plans such as `nix profile install nixpkgs#...` for mapped tools when no more appropriate native plan is selected.

This is not a NixOS configuration editor. DevDoctor does not modify `configuration.nix`, flakes, Home Manager configuration, or system generations.

Fixture coverage: `nix-user-profile`.

## Flatpak

DevDoctor detects **Flatpak** and includes it in update/diagnostic policy. Flatpak is suitable for mapped desktop applications, not arbitrary CLI/system dependencies.

Fixture coverage: `flatpak-only`.

## Mixed package-manager environments

DevDoctor reports suspicious overlap instead of picking a system manager based solely on PATH order. Atomic host + DNF is a high-severity policy conflict because DNF must not be proposed for host mutation. Multiple native system managers are reported for review.

Fixture coverage: `mixed-system-managers`.

## Evidence levels

The release process uses these labels:

- **Unit/fixture verified**: deterministic manager policy and command planning are covered by tests.
- **Clean-wheel verified**: the built wheel installs and the CLI starts in a new virtualenv.
- **Host integration verified**: CI ran against a real distribution/container with that package manager present.
- **Manual hardware/desktop verification**: tested on an actual workstation image such as Bazzite.

Do not promote a distro to a stronger level unless the corresponding job or manual report exists for the release being documented.
