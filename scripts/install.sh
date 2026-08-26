#!/usr/bin/env sh
set -eu

PACKAGE="devdoctor-workstation"
REQUESTED_VERSION="latest"
INSTALL_SOURCE="pypi"
ASSUME_YES=0
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
BASE_DIR="$DATA_HOME/devdoctor"
REPOSITORY="imedkablavi/DevDoctor"

usage() {
  cat <<'EOF'
Usage: install.sh [--version VERSION] [--source pypi|github] [--yes]

Installs DevDoctor into a user-owned virtual environment and links
~/.local/bin/devdoctor (or $XDG_BIN_HOME/devdoctor). No sudo is used.

Sources:
  pypi    Install devdoctor-workstation from PyPI.
  github  Download the exact release wheel and SHA256SUMS from GitHub,
          verify the wheel, then install it.

The installer previews the action and asks for confirmation unless --yes is given.
A GitHub release install requires an explicit version.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      [ "$#" -ge 2 ] || { echo "--version requires a value" >&2; exit 2; }
      REQUESTED_VERSION="$2"
      shift 2
      ;;
    --source)
      [ "$#" -ge 2 ] || { echo "--source requires a value" >&2; exit 2; }
      INSTALL_SOURCE="$2"
      shift 2
      ;;
    --yes|-y)
      ASSUME_YES=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$INSTALL_SOURCE" in
  pypi|github) ;;
  *)
    echo "Unsupported source: $INSTALL_SOURCE (use pypi or github)" >&2
    exit 2
    ;;
esac

if [ "$INSTALL_SOURCE" = "github" ] && [ "$REQUESTED_VERSION" = "latest" ]; then
  echo "GitHub release installs require --version VERSION." >&2
  exit 2
fi

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required. Install Python 3.11+ with your distribution package manager." >&2
  exit 1
}

PYTHON_OK="$(python3 -c 'import sys; print(int(sys.version_info >= (3, 11)))')"
[ "$PYTHON_OK" = "1" ] || {
  echo "DevDoctor requires Python 3.11 or newer." >&2
  exit 1
}

VENV_PROBE="$(mktemp -d "${TMPDIR:-/tmp}/devdoctor-venv-check.XXXXXX")" || {
  echo "Unable to create a temporary directory for the Python venv preflight." >&2
  exit 1
}
if ! python3 -m venv "$VENV_PROBE/env" >/dev/null 2>&1; then
  rm -rf "$VENV_PROBE"
  cat >&2 <<'EOF'
Python virtual-environment support is required but is not functional.
On Debian/Ubuntu install the matching python3-venv package, then retry.
DevDoctor will not install or modify system packages automatically.
EOF
  exit 1
fi
rm -rf "$VENV_PROBE"

SPEC="$PACKAGE"
if [ "$REQUESTED_VERSION" != "latest" ]; then
  SPEC="$PACKAGE==$REQUESTED_VERSION"
fi

LINK="$BIN_HOME/devdoctor"
if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
  echo "Refusing to replace non-symlink file: $LINK" >&2
  exit 1
fi

printf '%s\n' "DevDoctor install preview:" \
  "  source: $INSTALL_SOURCE" \
  "  package: $SPEC" \
  "  data directory: $BASE_DIR" \
  "  command link: $LINK" \
  "  privilege escalation: none"

if [ "$ASSUME_YES" -ne 1 ]; then
  if [ ! -t 0 ]; then
    echo "Refusing non-interactive install without --yes." >&2
    exit 2
  fi
  printf "Continue? [y/N] "
  read -r answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "Cancelled. No changes made."; exit 0 ;;
  esac
fi

mkdir -p "$BASE_DIR" "$BIN_HOME"
TEMP_DIR="$BASE_DIR/.installing-$$"
DOWNLOAD_DIR="$BASE_DIR/.download-$$"
BACKUP_DIR=""
FINAL_DIR=""
cleanup() {
  if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
    if [ -n "$FINAL_DIR" ] && [ ! -d "$FINAL_DIR" ]; then
      mv "$BACKUP_DIR" "$FINAL_DIR" 2>/dev/null || true
    else
      rm -rf "$BACKUP_DIR"
    fi
  fi
  rm -rf "$TEMP_DIR" "$DOWNLOAD_DIR"
}
trap cleanup EXIT HUP INT TERM

python3 -m venv "$TEMP_DIR"

if [ "$INSTALL_SOURCE" = "github" ]; then
  WHEEL_FILE="devdoctor_workstation-${REQUESTED_VERSION}-py3-none-any.whl"
  RELEASE_BASE="https://github.com/$REPOSITORY/releases/download/v$REQUESTED_VERSION"
  mkdir -p "$DOWNLOAD_DIR"

  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error \
      "$RELEASE_BASE/$WHEEL_FILE" -o "$DOWNLOAD_DIR/$WHEEL_FILE"
    curl --fail --location --silent --show-error \
      "$RELEASE_BASE/SHA256SUMS" -o "$DOWNLOAD_DIR/SHA256SUMS"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$RELEASE_BASE/$WHEEL_FILE" -O "$DOWNLOAD_DIR/$WHEEL_FILE"
    wget -q "$RELEASE_BASE/SHA256SUMS" -O "$DOWNLOAD_DIR/SHA256SUMS"
  else
    echo "curl or wget is required for a GitHub release install." >&2
    exit 1
  fi

  command -v sha256sum >/dev/null 2>&1 || {
    echo "sha256sum is required to verify a GitHub release install." >&2
    exit 1
  }

  grep "  $WHEEL_FILE\$" "$DOWNLOAD_DIR/SHA256SUMS" > "$DOWNLOAD_DIR/WHEEL.SHA256" || {
    echo "Release checksum manifest does not contain $WHEEL_FILE." >&2
    exit 1
  }
  (
    cd "$DOWNLOAD_DIR"
    sha256sum --check WHEEL.SHA256
  )
  INSTALL_SPEC="$DOWNLOAD_DIR/$WHEEL_FILE"
else
  INSTALL_SPEC="$SPEC"
fi

"$TEMP_DIR/bin/python" -m pip install --no-cache-dir "$INSTALL_SPEC"
ACTUAL_VERSION="$($TEMP_DIR/bin/python -c 'from importlib.metadata import version; print(version("devdoctor-workstation"))')"

if [ "$REQUESTED_VERSION" != "latest" ] && [ "$ACTUAL_VERSION" != "$REQUESTED_VERSION" ]; then
  echo "Installed version $ACTUAL_VERSION does not match requested $REQUESTED_VERSION." >&2
  exit 1
fi

"$TEMP_DIR/bin/devdoctor" --version >/dev/null

FINAL_DIR="$BASE_DIR/versions/$ACTUAL_VERSION"
mkdir -p "$BASE_DIR/versions"

if [ -d "$FINAL_DIR" ]; then
  BACKUP_DIR="$BASE_DIR/.replaced-$ACTUAL_VERSION-$$"
  mv "$FINAL_DIR" "$BACKUP_DIR"
fi

if ! mv "$TEMP_DIR" "$FINAL_DIR"; then
  if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ] && [ ! -d "$FINAL_DIR" ]; then
    mv "$BACKUP_DIR" "$FINAL_DIR" || true
  fi
  echo "Failed to activate the freshly validated DevDoctor environment." >&2
  exit 1
fi

if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
  rm -rf "$BACKUP_DIR"
  BACKUP_DIR=""
fi

ln -sfn "$FINAL_DIR/bin/devdoctor" "$LINK"
"$LINK" --version

trap - EXIT HUP INT TERM
rm -rf "$DOWNLOAD_DIR"

printf '%s\n' \
  "Installed DevDoctor $ACTUAL_VERSION." \
  "Re-running the same version replaces its virtual environment with a freshly validated one." \
  "Rollback across versions: repoint $LINK to a previous directory under $BASE_DIR/versions or remove the link."
