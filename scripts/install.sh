#!/usr/bin/env sh
set -eu

PACKAGE="devdoctor-cli"
REQUESTED_VERSION="latest"
ASSUME_YES=0
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${XDG_BIN_HOME:-$HOME/.local/bin}"
BASE_DIR="$DATA_HOME/devdoctor"

usage() {
  cat <<'EOF'
Usage: install.sh [--version VERSION] [--yes]

Installs DevDoctor into a user-owned virtual environment and links
~/.local/bin/devdoctor (or $XDG_BIN_HOME/devdoctor). No sudo is used.

The installer previews the action and asks for confirmation unless --yes is given.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      [ "$#" -ge 2 ] || { echo "--version requires a value" >&2; exit 2; }
      REQUESTED_VERSION="$2"
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

command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required. Install Python 3.11+ with your distribution package manager." >&2
  exit 1
}

PYTHON_OK="$(python3 -c 'import sys; print(int(sys.version_info >= (3, 11)))')"
[ "$PYTHON_OK" = "1" ] || {
  echo "DevDoctor requires Python 3.11 or newer." >&2
  exit 1
}

SPEC="$PACKAGE"
if [ "$REQUESTED_VERSION" != "latest" ]; then
  SPEC="$PACKAGE==$REQUESTED_VERSION"
fi

printf '%s\n' "DevDoctor install preview:" \
  "  package: $SPEC" \
  "  data directory: $BASE_DIR" \
  "  command link: $BIN_HOME/devdoctor" \
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
cleanup() {
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT HUP INT TERM

python3 -m venv "$TEMP_DIR"
"$TEMP_DIR/bin/python" -m pip install --upgrade pip >/dev/null
"$TEMP_DIR/bin/python" -m pip install --no-cache-dir "$SPEC"
ACTUAL_VERSION="$($TEMP_DIR/bin/python -c 'from importlib.metadata import version; print(version("devdoctor-cli"))')"
FINAL_DIR="$BASE_DIR/versions/$ACTUAL_VERSION"
mkdir -p "$BASE_DIR/versions"

if [ -d "$FINAL_DIR" ]; then
  rm -rf "$TEMP_DIR"
else
  mv "$TEMP_DIR" "$FINAL_DIR"
fi
trap - EXIT HUP INT TERM

LINK="$BIN_HOME/devdoctor"
if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
  echo "Refusing to replace non-symlink file: $LINK" >&2
  exit 1
fi
ln -sfn "$FINAL_DIR/bin/devdoctor" "$LINK"

"$LINK" --version
printf '%s\n' \
  "Installed DevDoctor $ACTUAL_VERSION." \
  "Rollback: repoint $LINK to a previous directory under $BASE_DIR/versions or remove the link."
