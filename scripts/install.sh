#!/usr/bin/env bash

# Albert Code Installation Script
# Clones the repo into a local install directory, creates a Python venv,
# installs albert-code in editable mode and exposes the launcher.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

INSTALL_DIR="${ALBERT_CODE_INSTALL_DIR:-$HOME/.local/share/albert-code}"
REPO_URL="${ALBERT_CODE_REPO:-https://github.com/obook/albert-code.git}"

function error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

function info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

function success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

function warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

function check_platform() {
    local platform
    platform=$(uname -s)

    if [[ "$platform" == "Linux" ]]; then
        info "Detected Linux platform"
    elif [[ "$platform" == "Darwin" ]]; then
        info "Detected macOS platform"
    else
        error "Unsupported platform: $platform"
        error "This installation script currently only supports Linux and macOS"
        exit 1
    fi
}

function check_python() {
    if ! command -v python3 &> /dev/null; then
        error "python3 not found. Please install Python 3.12 or higher."
        exit 1
    fi
    local version
    version=$(python3 -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
    info "Detected Python $version"
}

function clone_or_update_repo() {
    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "Updating existing albert-code clone in $INSTALL_DIR..."
        git -C "$INSTALL_DIR" pull --ff-only
    else
        info "Cloning albert-code into $INSTALL_DIR..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
}

function install_in_venv() {
    info "Creating Python venv and installing albert-code (editable mode)..."
    python3 -m venv "$INSTALL_DIR/.venv"
    # shellcheck disable=SC1091
    source "$INSTALL_DIR/.venv/bin/activate"
    pip install --upgrade --disable-pip-version-check pip > /dev/null
    pip install --disable-pip-version-check -e "$INSTALL_DIR"
    success "albert-code installed in editable mode."
}

function main() {
    echo
    echo "██████████████████░░"
    echo "██████████████████░░"
    echo "████  ██████  ████░░"
    echo "████    ██    ████░░"
    echo "████          ████░░"
    echo "████  ██  ██  ████░░"
    echo "██      ██      ██░░"
    echo "██████████████████░░"
    echo "██████████████████░░"
    echo
    echo "Starting Albert Code installation..."
    echo

    check_platform
    check_python
    clone_or_update_repo
    install_in_venv

    if [[ -x "$INSTALL_DIR/.venv/bin/albert-code" ]]; then
        success "Installation completed successfully!"
        echo
        echo "Launch albert-code with:"
        echo "  $INSTALL_DIR/albert-code.sh"
        echo
        echo "Or add an alias to your shell rc:"
        echo "  alias albert-code='$INSTALL_DIR/albert-code.sh'"
    else
        error "Installation completed but 'albert-code' entry point not found in venv"
        error "Check the install logs above."
        exit 1
    fi
}

main
