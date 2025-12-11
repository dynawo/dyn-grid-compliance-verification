#!/bin/bash
#
# This script automatically installs the DyCoV tool for end-users
# in Linux environments. It does not need root permissions.
# This version is optimized to use 'uv' for faster package installation.
#
# How it works:
#   * Creates a root dir ("dycov") under the $PWD. Everything, temporary or permanent, will go in there.
#   * Downloads Dynawo (our own validated Nightly release) and unpacks it under $PWD/dycov/dynawo.
#   * Shallow-clones the DyCoV repo under a temporary subdir, $PWD/dycov/repo_dycov.
#   * Builds & installs the app (and all of its Python dependencies) in a venv, under $PWD/dycov/dycov_venv.
#     (Note: it also edits the venv activation script to make sure this Dynawo is the first in the $PATH).
#   * Copies the examples under $PWD/dycov/examples.
#   * Also builds the User Manual and leaves it under $PWD/dycov/user_manual.
#   * Then deletes the temporarily cloned repo.
#
# The tool is then ready to be used, by sourcing $PWD/dycov/activate_dycov.
#
#
# (c) Rte 2024
#     Developed by Grupo AIA
#

# For saner programming: fail on error, on undefined variable, and prevent overwrite.
set -o nounset -o noclobber
set -o errexit -o pipefail

################################################################################
# Config variables
################################################################################

# DyCoV and Dynawo versions to install
REPO_URL="https://github.com/dynawo/dyn-grid-compliance-verification.git"
DYNAWO_ZIP_URL="https://github.com/dynawo/dynawo/releases/download/nightly/Dynawo_omc_v1.8.0.zip"
DYNAWO_SHA256SUM="d0236481e73bce24c2e830aee4c8e15e68dec7aafda895fd22da3403a50654b2"
# Edit these at Release time:
RELEASE_TAG="master"
DYNAWO_ZIP_FILE="Dynawo_omc_v1.8.0.zip"
#DYNAWO_ZIP_URL="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/$RELEASE_TAG/$DYNAWO_ZIP_FILE"
#DYNAWO_SHA256SUM="fbba80aa7ac6a990928b601e339a43ec49d538b956c97a51d038d1dcdea48768"

# Script State Variables
INSTALL_DIR="$PWD/dycov"
LOG_FILE_NAME=""
NON_INTERACTIVE=false
CUSTOM_ZIP_USED=false
DIRECT_URL=""
INSTALL_DYNAWO=true

# Local paths and filenames
INSTALL_DIR="$PWD/dycov"
TMP_LOCAL_REPO=$INSTALL_DIR/repo_dycov
VENV="dycov_venv"
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="installation_$DATETIME.log"

# Console message colors
RED='\033[1;31m'
GREEN='\033[1;32m'
NC='\033[0m'

################################################################################
# Helper Functions
RED="\\033[1;31m"
GREEN="\\033[1;32m"
NC="\\033[0m"

exec 6>&1 # Preserve original stdout

color_msg() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S'): $1"
    echo -e "${GREEN}$1${NC}" >&6
}

color_err_msg() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S'): $1"
    echo -e "\n\n${RED}$1${NC}" >&6
}

# Deletes the install directory in case of an error, preserving the log file.
cleanup_on_error() {
    color_err_msg "An error occurred. Cleaning up the installation directory..."
    if [ -d "$INSTALL_DIR" ]; then
        local log_path="$INSTALL_DIR/$LOG_FILE"
        if [ -f "$log_path" ]; then
            local parent_dir
            parent_dir=$(dirname "$INSTALL_DIR")
            mv "$log_path" "$parent_dir/"
            color_err_msg "Log file preserved at: $parent_dir/$LOG_FILE"
        fi
        rm -rf "$INSTALL_DIR"
        color_err_msg "Installation directory $INSTALL_DIR has been removed."
    fi
}

# Define and activate the error handler as early as possible
error_handler() {
    local exit_status=$1
    local line_num=$2
    color_err_msg "ERROR: The script failed with status ($exit_status) on line $line_num."
    cleanup_on_error
}
trap 'error_handler $? $LINENO' ERR

confirm_and_delete() {
    local target="$1"
    if [[ "$NON_INTERACTIVE" == true ]]; then
        color_msg "Non-interactive mode: deleting $target without prompting."
        rm -rf "$target"
        return
    fi
    local response
    echo -n -e "\n${RED}WARNING:${NC} This will permanently delete: ${target}. Are you sure? [y/N] " >&6
    read -r response <&6
    case "$response" in
        [yY][eE][sS] | [yY]) rm -rf "$target" ;;
        *) color_err_msg "Operation cancelled by user. Aborting script."; exit 1 ;;
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

# Argument parsing
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -r | --release)
            RELEASE_TAG="$2"
            shift
            shift
            ;;
        -u | --url)
            DIRECT_URL="$2"
            shift
            shift
            ;;
        -z | --zipfile)
            DYNAWO_ZIP_FILE="$2"
            CUSTOM_ZIP_USED=true
            shift
            shift
            ;;
        -d | --directory)
            INSTALL_DIR="$2"
            shift
            shift
            ;;
        -y | --yes)
            NON_INTERACTIVE=true
            shift
            ;;
        -h | --help) usage ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Variable definitions
TMP_LOCAL_REPO=$INSTALL_DIR/repo_dycov
VENV="dycov_venv"
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG_FILE_NAME="installation_$DATETIME.log"
LOG="$INSTALL_DIR/$LOG_FILE_NAME"
DYNAWO_ZIP_URL="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/$RELEASE_TAG/$DYNAWO_ZIP_FILE"

#######################################
# START OF THE INSTALLATION LOGIC
#######################################

# 1. Directory and Log Preparation
if [ -d "$INSTALL_DIR" ]; then
    echo -e "\n${RED}ERROR: The installation directory already exists: $INSTALL_DIR${NC}" >&6
    confirm_and_delete "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"

# Now that the log file dir exists, set up redirections:
exec 6>&1                       # Link file descriptor #6 with stdout. Saves stdout.
exec > "$INSTALL_DIR/$LOG_FILE" # stdout redirected to the log file
exec 7>&2                       # Link file descriptor #7 with stderr. Saves stderr.
exec 2>&1                       # stderr redirected to the log file too
# Reminder of how to restore stderr and stdout in case you need it elsewhere in the script:
#exec 1>&6 6>&-    # Restore stdout and close fd 6
#exec 2>&7 7>&-    # Restore stderr and close fd 7

################################################################################
# Check if we have all the required system dependencies
################################################################################
color_msg "Step 0: Verifying system dependencies..."
for cmd in curl unzip gcc g++ cmake pdflatex latexmk git awk; do
    if ! which "$cmd" > /dev/null; then
        color_err_msg "ERROR: Required command not found: $cmd. Please install it."
        exit 1
    fi
done
find_python_cmd
if [ -z "$python_cmd" ]; then
    color_err_msg "ERROR: No valid Python interpreter found (3.9+ required)."
    exit 1
fi
color_msg "Dependencies verified successfully."

color_msg ""
color_msg "Starting the installation of the DyCoV tool in: $INSTALL_DIR"
if [ -n "$DIRECT_URL" ]; then
    color_msg "    * Installation Method: Direct URL"
    color_msg "    * Source URL: $DIRECT_URL"
else
    color_msg "    * Installation Method: Git Clone"
    color_msg "    * Using Release Tag: $RELEASE_TAG"
fi
color_msg "    * Using Dynawo ZIP file: $DYNAWO_ZIP_FILE"
color_msg "    * Python Interpreter: $($python_cmd --version) (command: \"$python_cmd\")"
color_msg "    * To view detailed progress: tail -f $INSTALL_DIR/$LOG_FILE"
color_msg ""

################################################################################
# Download and Extraction of Dynawo
################################################################################
color_msg "Step 1: Downloading and extracting Dynawo..."
cd "$INSTALL_DIR"

# Ask the user only if non-interactive mode is disabled.
if [[ "$NON_INTERACTIVE" == false ]]; then
    echo -n -e "\nDo you want to download and install Dynawo? (Required for some examples) [Y/n] " >&6
    read -r response <&6

    case "$response" in
        [nN][oO] | [nN])
            INSTALL_DYNAWO=false
            color_msg "User chose not to install Dynawo. Skipping."
            ;;
        *)
            # Any other response (including Enter) is considered a 'Yes'.
            INSTALL_DYNAWO=true
            color_msg "User confirmed Dynawo installation."
            ;;
    esac
else
    color_msg "Non-interactive mode enabled, proceeding with Dynawo installation automatically."
fi

# Run the Dynawo installation block only if the variable is true.
if [[ "$INSTALL_DYNAWO" == true ]]; then
    curl -O -L --fail "$DYNAWO_ZIP_URL"
    if [[ "$CUSTOM_ZIP_USED" == true ]]; then
        color_msg "NOTICE: Skipping checksum verification for custom Dynawo ZIP file."
    else
        color_msg "Verifying Dynawo ZIP file checksum..."
        SHA256SUM_CALCULATED=$(sha256sum "$DYNAWO_ZIP_FILE" | cut -d" " -f1)
        if [ "$SHA256SUM_CALCULATED" != "$DYNAWO_SHA256SUM" ]; then
            color_err_msg "FATAL ERROR: Checksum mismatch. Expected: '$DYNAWO_SHA256SUM', Got: '$SHA256SUM_CALCULATED'. Aborting for security."
            exit 1
        fi
        color_msg "Checksum verified successfully."
    fi

    unzip -q "$DYNAWO_ZIP_FILE"
    rm -rf "$DYNAWO_ZIP_FILE"
    color_msg "Dynawo downloaded and installed."

    # Temp patch for Boost pthreads header file (needed if gcc version is 12 or higher)
    GNU_MAJOR=$(g++ -v 2>&1 | grep -E '^gcc version ' | cut -d" " -f 3 | cut -d"." -f1)
    if [ "$GNU_MAJOR" -gt 11 ]; then
        BOOST_HEADER=./dynawo/include/boost/thread/pthread/thread_data.hpp
        if [ -f "$BOOST_HEADER" ] && grep -q '#if PTHREAD_STACK_MIN > 0$' "$BOOST_HEADER"; then
            color_msg "Applying compatibility patch for Boost and GCC > 11..."
            sed --in-place=.ORIG -E 's/^#if PTHREAD_STACK_MIN > 0$/#ifdef PTHREAD_STACK_MIN/' "$BOOST_HEADER"
        fi
    fi
fi

################################################################################
# Get the DyCoV Source Code
################################################################################
if [ -d "$TMP_LOCAL_REPO" ]; then
    confirm_and_delete "$TMP_LOCAL_REPO"
fi

if [ -n "$DIRECT_URL" ]; then
    color_msg "Step 2: Downloading DyCoV source code from direct URL..."

    SOURCE_ZIP_FILENAME="${DIRECT_URL##*/}"
    color_msg "Downloading as: $SOURCE_ZIP_FILENAME"

    curl -L --fail "$DIRECT_URL" -o "$SOURCE_ZIP_FILENAME"
    unzip -q "$SOURCE_ZIP_FILENAME"
    rm -f "$SOURCE_ZIP_FILENAME" # Changed to rm -f to avoid errors if it doesn't exist.

    UNZIPPED_DIR=$(find . -mindepth 1 -maxdepth 1 -type d ! -name 'dynawo')
    if [ -z "$UNZIPPED_DIR" ] || [ "$(echo "$UNZIPPED_DIR" | wc -l)" -ne 1 ]; then
        color_err_msg "ERROR: Could not determine the unzipped source directory. Expected a single directory."
        exit 1
    fi
    mv "$UNZIPPED_DIR" "$TMP_LOCAL_REPO"
    color_msg "Source code downloaded and prepared."
else
    color_msg "Step 2: Shallow-cloning the DyCoV repository (tag: $RELEASE_TAG)..."
    git clone --depth 1 --branch "$RELEASE_TAG" "$REPO_URL" "$TMP_LOCAL_REPO"
    color_msg "Repository cloned."
fi

################################################################################
# Create Virtual Environment and Install
################################################################################
color_msg "Step 3: Creating virtual environment and installing the application..."
if [ -d "${INSTALL_DIR}/$VENV" ]; then
    confirm_and_delete "${INSTALL_DIR}/$VENV"
fi
cd "$INSTALL_DIR"

# 1. Create a standard venv first
"$python_cmd" -m venv "$VENV"

# 2. Activate it and install uv into it
# shellcheck source=/dev/null
source "$VENV"/bin/activate
pip install -q uv

# 3. Use uv to install the application from the cloned repo
uv pip install -q "$TMP_LOCAL_REPO"

# 4. Deactivate for subsequent steps
deactivate
color_msg "Virtual environment created and application installed successfully."

# Customize the Activation Script
color_msg "Step 4: Customizing the environment activation script..."
ACTIVATE_SCRIPT="$INSTALL_DIR/$VENV"/bin/activate

# Conditionally define the user's PATH.
# The dynawo directory is only added if it was installed.
if [[ "$INSTALL_DYNAWO" == true ]]; then
    USER_PATH="$INSTALL_DIR/dynawo:\$VIRTUAL_ENV/bin:\$PATH"
else
    USER_PATH="\$VIRTUAL_ENV/bin:\$PATH"
fi
sed -E --in-place=.ORIG -e "s%^PATH=.*%PATH=\"$USER_PATH\"%" "$ACTIVATE_SCRIPT"
cp "$ACTIVATE_SCRIPT" "$INSTALL_DIR"/activate_dycov

# shellcheck source=/dev/null
source "$INSTALL_DIR"/activate_dycov
echo -e "\n\n--- LIST OF PACKAGES INSTALLED IN THE VIRTUAL ENVIRONMENT ---"
uv pip list
echo -e "---------------------------------------------------------\n\n"
deactivate
color_msg "Activation script customized."

################################################################################
# Copy Examples and Build the Manual
################################################################################
color_msg "Step 5: Installing examples and building the manual..."
cp -a "$TMP_LOCAL_REPO"/examples "$INSTALL_DIR"/
# shellcheck source=/dev/null
source "$INSTALL_DIR"/activate_dycov
uv pip install -q sphinx
cd "$TMP_LOCAL_REPO"/docs/manual
make latexpdf > /dev/null 2>&1
make html > /dev/null 2>&1
deactivate
mkdir -p "$INSTALL_DIR"/manual
mv "$TMP_LOCAL_REPO"/docs/manual/build/html "$INSTALL_DIR"/manual/
mv "$TMP_LOCAL_REPO"/docs/manual/build/latex/dycov.pdf "$INSTALL_DIR"/manual/
color_msg "Examples and manuals are ready."

################################################################################
# Final Cleanup
################################################################################
color_msg "Step 6: Performing final cleanup..."
rm -rf "$TMP_LOCAL_REPO"
color_msg "Final cleanup finished."
color_msg ""
color_msg "INSTALLATION COMPLETED SUCCESSFULLY!"
color_msg "To start using the tool, run: source $INSTALL_DIR/activate_dycov"
color_msg ""
