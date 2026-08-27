from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.sh"


def test_installer_has_valid_posix_shell_syntax() -> None:
    subprocess.run(("sh", "-n", str(INSTALLER)), check=True)


def test_installer_preflights_venv_before_creating_devdoctor_directories() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    preflight = text.index('python3 -m venv "$VENV_PROBE/env"')
    install_dirs = text.index('mkdir -p "$BASE_DIR" "$BIN_HOME"')

    assert preflight < install_dirs
    assert "python3-venv" in text
    assert "will not install or modify system packages automatically" in text


def test_installer_never_moves_or_renames_the_created_virtualenv() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    creation = text.index('python3 -m venv "$ENV_DIR"')
    validation = text.index('"$ENV_DIR/bin/devdoctor" --version >/dev/null')
    activation = text.index('ln -sfn "$ENV_DIR/bin/devdoctor" "$LINK"')

    assert creation < validation < activation
    assert 'mv "$ENV_DIR"' not in text
    assert 'mv "$TEMP_DIR"' not in text
    assert "console-script shebangs embed this absolute path" in text


def test_installer_serializes_activation_and_rolls_back_symlinks() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    assert 'LOCK_DIR="$BASE_DIR/.install.lock"' in text
    assert 'mkdir "$LOCK_DIR"' in text
    assert 'OLD_LINK_TARGET="$(readlink "$LINK"' in text
    assert 'OLD_VERSION_TARGET="$(readlink "$VERSION_LINK"' in text
    assert 'restore_symlink "$OLD_LINK_TARGET" "$LINK"' in text
    assert 'restore_symlink "$OLD_VERSION_TARGET" "$VERSION_LINK"' in text
    assert 'rm -rf "$ENV_DIR"' in text
    assert "trap cleanup EXIT" in text
    assert "trap 'exit 130' INT" in text
    assert "trap 'exit 143' TERM" in text


def test_installer_uses_current_distribution_and_normalized_wheel_name() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    assert 'PACKAGE="devdoctor-workstation"' in text
    assert 'WHEEL_FILE="devdoctor_workstation-${REQUESTED_VERSION}-py3-none-any.whl"' in text
    assert 'version("devdoctor-workstation")' in text
    assert "devdoctor-cli" not in text
