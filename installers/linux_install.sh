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

# --- Default Configuration Variables ---
RELEASE_TAG="v0.8.1"
DYNAWO_ZIP_FILE="Dynawo_omc_v1.8.0.zip"
DYNAWO_CHECKSUM="2e2f36920d729413126ae3dbea94e34e11b6ab33"
REPO_URL="https://github.com/dynawo/dyn-grid-compliance-verification.git"

# --- Script State Variables ---
INSTALL_DIR="$PWD/dycov"
NON_INTERACTIVE=false
CUSTOM_ZIP_USED=false
DIRECT_URL="" # Variable for direct source code download.

# --- Helper Functions ---
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

# Cleans up the installation directory in case of an error.
cleanup_on_error() {
    color_err_msg "An error occurred. Cleaning up the installation directory..."
    if [ -d "$INSTALL_DIR" ]; then
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

# Searches for a compatible Python interpreter (3.9+).
find_python_cmd() {
    for INTERPRETER in python python3 python3.12 python3.11 python3.10 python3.9; do
        if which $INTERPRETER > /dev/null; then
            if $INTERPRETER --version 2>&1 | grep -Eq '(Python 3\.9\.|Python 3\.1[0-3].)'; then
                python_cmd="$INTERPRETER"
                return
            fi
        fi
    done
    python_cmd=""
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

# --- Command-Line Argument Parsing ---
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

# --- Definition of Dependent Variables ---
TMP_LOCAL_REPO=$INSTALL_DIR/repo_dycov
VENV="dycov_venv"
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG=$INSTALL_DIR/installation_$DATETIME.log
DYNAWO_ZIP_URL="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/$RELEASE_TAG/$DYNAWO_ZIP_FILE"


#######################################
# START OF THE INSTALLATION LOGIC
#######################################

# 1. Directory and Log Preparation
if [ -d "$INSTALL_DIR" ]; then
    # The directory exists. We'll use the 'confirm_and_delete' helper function.
    # It will prompt the user, handle non-interactive mode, and exit if the user declines.
    echo -e "\n${RED}ERROR: The installation directory already exists: $INSTALL_DIR${NC}" >&6
    confirm_and_delete "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"

# Now, redirect stdout and stderr to the log file.
# Messages for the user will continue to be sent to the console via FD 6.
exec >"$LOG"
exec 7>&2
exec 2>&1

# 2. System Dependency Check
color_msg "Step 0: Verifying system dependencies..."
for cmd in curl unzip gcc g++ cmake pdflatex latexmk git; do
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
color_msg "    * To view detailed progress: tail -f $LOG"
color_msg ""

# 3. Download and Extraction of Dynawo
color_msg "Step 1: Downloading and extracting Dynawo..."
cd "$INSTALL_DIR"
curl -O -L --fail "$DYNAWO_ZIP_URL"

if [[ "$CUSTOM_ZIP_USED" == true ]]; then
    color_msg "NOTICE: Skipping checksum verification for custom Dynawo ZIP file."
else
    color_msg "Verifying Dynawo ZIP file checksum..."
    CHECKSUM_CALCULATED=$(shasum "$DYNAWO_ZIP_FILE" | cut -d" " -f1)
    if [ "$CHECKSUM_CALCULATED" != "$DYNAWO_CHECKSUM" ]; then
        color_err_msg "FATAL ERROR: Checksum mismatch. Expected: '$DYNAWO_CHECKSUM', Got: '$CHECKSUM_CALCULATED'. Aborting for security."
        exit 1
    fi
    color_msg "Checksum verified successfully."
fi

unzip -q "$DYNAWO_ZIP_FILE"
rm -rf "$DYNAWO_ZIP_FILE"
color_msg "Dynawo downloaded and installed."

# Temporary patch for Boost
GNU_MAJOR=$(g++ -v 2>&1 | grep -E '^gcc version ' | cut -d" " -f 3 | cut -d"." -f1)
if [ "$GNU_MAJOR" -gt 11 ]; then
    BOOST_HEADER=./dynawo/include/boost/thread/pthread/thread_data.hpp
    if [ -f "$BOOST_HEADER" ] && grep -q '#if PTHREAD_STACK_MIN > 0$' "$BOOST_HEADER"; then
        color_msg "Applying compatibility patch for Boost and GCC > 11..."
        sed --in-place=.ORIG -E 's/^#if PTHREAD_STACK_MIN > 0$/#ifdef PTHREAD_STACK_MIN/' "$BOOST_HEADER"
    fi
fi

# 4. Get the DyCoV Source Code
if [ -d "$TMP_LOCAL_REPO" ]; then
    confirm_and_delete "$TMP_LOCAL_REPO"
fi

if [ -n "$DIRECT_URL" ]; then
    # --- NEW LOGIC: Download from Direct URL ---
    color_msg "Step 2: Downloading DyCoV source code from direct URL..."
    
    # Extract the filename from the URL (e.g., GFM-changes.zip)
    SOURCE_ZIP_FILENAME="${DIRECT_URL##*/}"
    color_msg "Downloading as: $SOURCE_ZIP_FILENAME"

    curl -L --fail "$DIRECT_URL" -o "$SOURCE_ZIP_FILENAME"
    unzip -q "$SOURCE_ZIP_FILENAME"
    confirm_and_delete "$SOURCE_ZIP_FILENAME"
    
    # Find the name of the unzipped directory and rename it
    UNZIPPED_DIR=$(find . -mindepth 1 -maxdepth 1 -type d ! -name 'dynawo')
    if [ -z "$UNZIPPED_DIR" ] || [ "$(echo "$UNZIPPED_DIR" | wc -l)" -ne 1 ]; then
        color_err_msg "ERROR: Could not determine the unzipped source directory. Expected a single directory."
        exit 1
    fi
    mv "$UNZIPPED_DIR" "$TMP_LOCAL_REPO"
    color_msg "Source code downloaded and prepared."
else
    # --- ORIGINAL LOGIC: Clone with Git ---
    color_msg "Step 2: Cloning the DyCoV repository (tag: $RELEASE_TAG)..."
    git clone --depth 1 --branch "$RELEASE_TAG" "$REPO_URL" "$TMP_LOCAL_REPO"
    color_msg "Repository cloned."
fi

# 5. Create Virtual Environment and Install
color_msg "Step 3: Creating virtual environment and installing the application..."
if [ -d "${INSTALL_DIR}/$VENV" ]; then
    confirm_and_delete "${INSTALL_DIR}/$VENV"
fi
cd "$INSTALL_DIR"
"$TMP_LOCAL_REPO"/build_and_install.sh
color_msg "Virtual environment created and application installed."

# 6. Customize the Activation Script
color_msg "Step 4: Customizing the environment activation script..."
ACTIVATE_SCRIPT="$INSTALL_DIR/$VENV"/bin/activate
USER_PATH="$INSTALL_DIR/dynawo:\$VIRTUAL_ENV/bin:\$PATH"
sed -E --in-place=.ORIG -e "s%^PATH=.*%PATH=\"$USER_PATH\"%" "$ACTIVATE_SCRIPT"
cp "$ACTIVATE_SCRIPT" "$INSTALL_DIR"/activate_dycov

# shellcheck source=/dev/null
source "$INSTALL_DIR"/activate_dycov
echo -e "\n\n--- LIST OF PACKAGES INSTALLED IN THE VIRTUAL ENVIRONMENT ---"
pip list
echo -e "---------------------------------------------------------\n\n"
deactivate
color_msg "Activation script customized."

# 7. Copy Examples and Build the Manual
color_msg "Step 5: Installing examples and building the manual..."
cp -a "$TMP_LOCAL_REPO"/examples "$INSTALL_DIR"/
# shellcheck source=/dev/null
source "$INSTALL_DIR"/activate_dycov
pip install sphinx
cd "$TMP_LOCAL_REPO"/docs/manual
make latexpdf > /dev/null
make html > /dev/null
deactivate
mkdir "$INSTALL_DIR"/manual
mv "$TMP_LOCAL_REPO"/docs/manual/build/html "$INSTALL_DIR"/manual/
mv "$TMP_LOCAL_REPO"/docs/manual/build/latex/dycov.pdf "$INSTALL_DIR"/manual/
color_msg "Examples and manuals are ready."

# 8. Final Cleanup
color_msg "Step 6: Performing final cleanup..."
confirm_and_delete "$TMP_LOCAL_REPO"
color_msg "Final cleanup finished."
color_msg ""
color_msg "INSTALLATION COMPLETED SUCCESSFULLY!"
color_msg "To start using the tool, run: source $INSTALL_DIR/activate_dycov"
color_msg ""