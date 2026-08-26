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


def test_installer_repairs_same_version_with_rollback_safe_swap() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    assert 'BACKUP_DIR="$BASE_DIR/.replaced-$ACTUAL_VERSION-$$"' in text
    assert 'mv "$FINAL_DIR" "$BACKUP_DIR"' in text
    assert 'mv "$TEMP_DIR" "$FINAL_DIR"' in text
    assert 'mv "$BACKUP_DIR" "$FINAL_DIR"' in text
    assert '"$TEMP_DIR/bin/devdoctor" --version >/dev/null' in text


def test_installer_restores_environment_and_link_until_activation_commits() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    activation_check = text.index('"$LINK" --version')
    activation_commit = text.index("ACTIVATED=1")
    backup_delete = text.index('rm -rf "$BACKUP_DIR"', activation_commit)

    assert activation_check < activation_commit < backup_delete
    assert 'OLD_LINK_TARGET="$(readlink "$LINK"' in text
    assert 'ln -sfn "$OLD_LINK_TARGET" "$LINK"' in text
    assert 'rm -rf "$FINAL_DIR"' in text
    assert "trap cleanup EXIT" in text
    assert "trap 'exit 130' INT" in text
    assert "trap 'exit 143' TERM" in text


def test_installer_uses_current_distribution_and_normalized_wheel_name() -> None:
    text = INSTALLER.read_text(encoding="utf-8")

    assert 'PACKAGE="devdoctor-workstation"' in text
    assert 'WHEEL_FILE="devdoctor_workstation-${REQUESTED_VERSION}-py3-none-any.whl"' in text
    assert 'version("devdoctor-workstation")' in text
    assert "devdoctor-cli" not in text
