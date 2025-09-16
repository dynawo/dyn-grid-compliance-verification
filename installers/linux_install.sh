#!/bin/bash
#
# This script automatically installs the DyCoV tool for end-users
# in Linux environments. It does not need root permissions.
#
# (c) Rte 2024
#     Developed by Grupo AIA
#

# For saner programming: fail on error, on undefined variable, and prevent overwrite.
set -o nounset -o noclobber
set -o errexit -o pipefail

# Default Configuration Variables
RELEASE_TAG="v0.8.1"
DYNAWO_ZIP_FILE="Dynawo_omc_v1.8.0.zip"
DYNAWO_CHECKSUM="2e2f36920d729413126ae3dbea94e34e11b6ab33"
REPO_URL="https://github.com/dynawo/dyn-grid-compliance-verification.git"

# Script State Variables
INSTALL_DIR="$PWD/dycov"
LOG_FILE_NAME="" # Will be set later
NON_INTERACTIVE=false
CUSTOM_ZIP_USED=false
DIRECT_URL="" # Variable for direct source code download.
INSTALL_DYNAWO=true # Controls the optional installation of Dynawo.

# Helper Functions
RED="\\033[1;31m"
GREEN="\\033[1;32m"
NC="\\033[0m"

# Make a copy of the original stdout for writing to the console later.
# This must be done before any function uses >&6.
exec 6>&1

# Displays a message on the console and saves it to the log.
color_msg() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S'): $1"
    echo -e "${GREEN}$1${NC}" >&6
}

# Displays an error message on the console and saves it to the log.
color_err_msg() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S'): $1"
    echo -e "\n\n${RED}$1${NC}" >&6
}

# Cleans up the installation directory in case of an error, preserving the log file.
cleanup_on_error() {
    color_err_msg "An error occurred. Cleaning up the installation directory..."
    if [ -d "$INSTALL_DIR" ]; then
        local log_path="$INSTALL_DIR/$LOG_FILE_NAME"
        if [ -f "$log_path" ]; then
            local parent_dir
            parent_dir=$(dirname "$INSTALL_DIR")
            mv "$log_path" "$parent_dir/"
            color_err_msg "Log file preserved at: $parent_dir/$LOG_FILE_NAME"
        fi
        rm -rf "$INSTALL_DIR"
        color_err_msg "Installation directory $INSTALL_DIR has been removed."
    fi
}

# Error handler activated by trap.
error_handler() {
    local exit_status=$1
    local line_num=$2
    color_err_msg "ERROR: The script failed with status ($exit_status) on line $line_num."
    cleanup_on_error
}

# Activates the error handler for any script failure.
trap 'error_handler $? $LINENO' ERR

# Asks for confirmation before deleting, unless --yes mode is active.
confirm_and_delete() {
    local target="$1"
    
    if [[ "$NON_INTERACTIVE" == true ]]; then
        color_msg "Non-interactive mode: deleting $target without prompting."
        rm -rf "$target"
        return
    fi
    
    local response
    echo -n -e "\n${RED}WARNING:${NC} This will permanently delete: ${target}. Are you sure you want to continue? [y/N] " >&6
    read -r response <&6
    
    case "$response" in
        [yY][eE][sS] | [yY])
            color_msg "User confirmed deletion of: $target. Deleting..."
            rm -rf "$target"
            ;;
        *)
            color_err_msg "Operation cancelled by user. Aborting script."
            exit 1
            ;;
    esac
}

# Searches for the newest compatible Python interpreter (3.9+).
find_python_cmd() {
    local best_interpreter=""
    local available_interpreters=()

    # Find all available and compatible interpreters
    for interpreter in python3.12 python3.11 python3.10 python3.9 python3 python; do
        if which "$interpreter" > /dev/null; then
            if "$interpreter" --version 2>&1 | grep -Eq '(Python 3\.9\.|Python 3\.1[0-9]+\.)'; then
                # Store the full path to avoid ambiguity
                available_interpreters+=("$(which "$interpreter")")
            fi
        fi
    done

    # If we found any, sort them by version and pick the best one.
    if [ ${#available_interpreters[@]} -gt 0 ]; then
        # Get unique paths, get versions, sort, and extract the path of the newest one
        best_interpreter=$(printf "%s\n" "${available_interpreters[@]}" | sort -u | while read -r interp; do
            echo "$($interp --version 2>&1 | awk '{print $2}') $interp"
        done | sort -V -r | head -n 1 | awk '{print $2}')
    fi
    
    python_cmd="$best_interpreter"
}

# Displays the script's help message.
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -r, --release TAG      The Git release tag to clone (default: $RELEASE_TAG). Ignored if --url is used."
    echo "  -u, --url URL          Direct URL to a ZIP file of the source code. Overrides the --release method."
    echo "  -z, --zipfile FILE     The name of the Dynawo ZIP file (default: $DYNAWO_ZIP_FILE)."
    echo "  -d, --directory PATH   Directory where the installation will be performed (default: ./dycov)."
    echo "  -y, --yes              Non-interactive mode, accepts all confirmations."
    echo "  -h, --help             Show this help message."
    exit 0
}

# Command-Line Argument Parsing
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -r|--release) RELEASE_TAG="$2"; shift; shift;;
        -u|--url) DIRECT_URL="$2"; shift; shift;;
        -z|--zipfile) DYNAWO_ZIP_FILE="$2"; CUSTOM_ZIP_USED=true; shift; shift;;
        -d|--directory) INSTALL_DIR="$2"; shift; shift;;
        -y|--yes) NON_INTERACTIVE=true; shift;;
        -h|--help) usage;;
        *) echo "Unknown option: $1"; usage;;
    esac
done

# Definition of Dependent Variables
TMP_LOCAL_REPO=$INSTALL_DIR/repo_dycov
VENV="dycov_venv"
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG_FILE_NAME="installation_$DATETIME.log" # Assign the name here to be used by the error handler
LOG="$INSTALL_DIR/$LOG_FILE_NAME"
DYNAWO_ZIP_URL