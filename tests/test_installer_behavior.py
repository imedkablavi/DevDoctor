from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.sh"
VERSION = "1.2.0rc1"


def _write_fake_python(fake_bin: Path) -> None:
    fake_bin.mkdir(parents=True)
    python3 = fake_bin / "python3"
    python3.write_text(
        r"""#!/bin/sh
set -eu

if [ "${1:-}" = "-c" ]; then
  echo 1
  exit 0
fi

if [ "${1:-}" = "-m" ] && [ "${2:-}" = "venv" ]; then
  if [ "${DEVDOCTOR_FAKE_VENV_FAIL:-0}" = "1" ]; then
    exit 1
  fi
  target="$3"
  mkdir -p "$target/bin"
  cat > "$target/bin/python" <<'PYTHON'
#!/bin/sh
set -eu
BIN_DIR="$(dirname "$0")"

if [ "${1:-}" = "-m" ] && [ "${2:-}" = "pip" ]; then
  cat > "$BIN_DIR/devdoctor" <<'DEVDOCTOR'
#!/bin/sh
RESOLVED="$(readlink -f "$0" 2>/dev/null || printf '%s' "$0")"
case "$RESOLVED" in
  *".installing-"*)
    echo "DevDoctor 1.2.0rc1"
    exit 0
    ;;
esac
if [ "${DEVDOCTOR_FAKE_FAIL_FINAL:-0}" = "1" ]; then
  exit 42
fi
echo "DevDoctor 1.2.0rc1"
DEVDOCTOR
  chmod +x "$BIN_DIR/devdoctor"
  exit 0
fi

if [ "${1:-}" = "-c" ]; then
  echo "1.2.0rc1"
  exit 0
fi

exit 2
PYTHON
  chmod +x "$target/bin/python"
  exit 0
fi

exit 2
""",
        encoding="utf-8",
    )
    python3.chmod(0o755)


def _installer_env(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    fake_bin = tmp_path / "fake-bin"
    _write_fake_python(fake_bin)

    data_home = tmp_path / "data"
    bin_home = tmp_path / "bin"
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "XDG_DATA_HOME": str(data_home),
            "XDG_BIN_HOME": str(bin_home),
            "PATH": f"{fake_bin}:{env['PATH']}",
        }
    )
    return env, data_home, bin_home


def _run_installer(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (
            "sh",
            str(INSTALLER),
            "--source",
            "pypi",
            "--version",
            VERSION,
            "--yes",
        ),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def test_installer_venv_preflight_fails_before_devdoctor_state_is_created(
    tmp_path: Path,
) -> None:
    env, data_home, bin_home = _installer_env(tmp_path)
    env["DEVDOCTOR_FAKE_VENV_FAIL"] = "1"

    result = _run_installer(env)

    assert result.returncode != 0
    assert "python3-venv" in result.stderr
    assert not (data_home / "devdoctor").exists()
    assert not (bin_home / "devdoctor").exists()


def test_installer_activates_fresh_validated_environment(tmp_path: Path) -> None:
    env, data_home, bin_home = _installer_env(tmp_path)

    result = _run_installer(env)

    final = data_home / "devdoctor" / "versions" / VERSION
    link = bin_home / "devdoctor"
    assert result.returncode == 0, result.stderr
    assert (final / "bin" / "devdoctor").is_file()
    assert link.is_symlink()
    assert link.readlink() == final / "bin" / "devdoctor"
    assert "Installed DevDoctor 1.2.0rc1." in result.stdout


def test_installer_restores_previous_environment_and_link_on_activation_failure(
    tmp_path: Path,
) -> None:
    env, data_home, bin_home = _installer_env(tmp_path)
    versions = data_home / "devdoctor" / "versions"
    previous = versions / "1.1.0"
    same_version = versions / VERSION
    previous.mkdir(parents=True)
    same_version.mkdir(parents=True)
    (same_version / "old-marker").write_text("keep me", encoding="utf-8")

    bin_home.mkdir(parents=True)
    link = bin_home / "devdoctor"
    old_target = previous / "bin" / "devdoctor"
    link.symlink_to(old_target)
    env["DEVDOCTOR_FAKE_FAIL_FINAL"] = "1"

    result = _run_installer(env)

    assert result.returncode != 0
    assert (same_version / "old-marker").read_text(encoding="utf-8") == "keep me"
    assert link.is_symlink()
    assert link.readlink() == old_target
    assert not list((data_home / "devdoctor").glob(".replaced-*"))
    assert not list((data_home / "devdoctor").glob(".installing-*"))
