
#!/bin/bash
#
# This script automatically installs the DyCoV tool for end-users
# in Linux environments. It does not need root permissions.
# This version is optimized to use 'uv' for faster package installation.
#
# How it works:
#   * Creates a root dir ("dycov") under the $PWD.
#   * Downloads Dynawo (our own validated Nightly release) and unpacks it under $PWD/dycov/dynawo.
#   * Gets DyCoV source (via Git, URL, or Local ZIP) under a temporary subdir.
#   * Builds & installs the app in a venv using 'uv'.
#   * Edits the venv activation script to include Dynawo in the PATH.
#   * Copies examples and builds the manual.
#
# (c) Rte 2024
#     Developed by Grupo AIA
#

# Fail on error, on undefined variable, and prevent overwrite.
set -o nounset -o noclobber
set -o errexit -o pipefail

################################################################################
# Config variables
################################################################################

# DyCoV and Dynawo versions to install
TARGET_BRANCH="master"
REPO_URL="https://github.com/dynawo/dyn-grid-compliance-verification.git"
DYNAWO_ZIP_URL_DEFAULT="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/$TARGET_BRANCH/Dynawo_omc_v1.8.0.zip"
DYNAWO_SHA256SUM="fbba80aa7ac6a990928b601e339a43ec49d538b956c97a51d038d1dcdea48768"
# Default branch is master
DYNAWO_ZIP_FILE="Dynawo_omc_v1.8.0.zip"

# Script State Variables
INSTALL_DIR_BASE="$PWD/dycov"
NON_INTERACTIVE=false
CUSTOM_ZIP_USED=false
DIRECT_URL=""
LOCAL_SOURCE_ZIP=""
INSTALL_DYNAWO=true

# Local paths
INSTALL_DIR="$INSTALL_DIR_BASE"
TMP_LOCAL_REPO="$INSTALL_DIR/repo_dycov"
VENV="dycov_venv"
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG_FILE_NAME="installation_$DATETIME.log"
python_cmd=""

# Console message colors
RED='\033[1;31m'
GREEN='\033[1;32m'
NC='\033[0m'

# Backup file descriptor for the original stdout (console output)
# We use FD 6 to print to the user's screen regardless of log redirection
# --- prepare console fds early (robust under pipes / non-tty) ---
if [ -t 1 ]; then
  exec 6>/dev/tty || exec 6>&1
else
  exec 6>/dev/null
fi

# Optional: prepare a backup for stderr similar to fd6 (for cleanup restore)
if [ -t 2 ]; then
  exec 7>/dev/tty || true
else
  exec 7>/dev/null
fi
# --- end console fd setup ---

################################################################################
# Helper Functions
################################################################################

color_msg() {
    local msg="$1"
    # 1. Log to log file (stdout, which is redirected to file later)
    echo -e "$(date '+%Y-%m-%d %H:%M:%S'): $msg"
    # 2. Print to console (original stdout kept in fd 6)
    echo -e "${GREEN}${msg}${NC}" >&6
}

color_err_msg() {
    local msg="$1"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S'): $msg"
    echo -e "\n\n${RED}${msg}${NC}" >&6
}

cleanup_on_error() {
    local exit_status="$1"
    # Print cleanup message to console directly (FD 6)
    echo -e "\n${RED}An error occurred. Cleaning up the installation directory...${NC}" >&6
    
    local log_path="$INSTALL_DIR/$LOG_FILE_NAME"

    if [ -d "$INSTALL_DIR" ]; then
        if [ -f "$log_path" ]; then
            local parent_dir
            parent_dir=$(dirname "$INSTALL_DIR")
            mv "$log_path" "$parent_dir/" 2>/dev/null || true
            echo -e "${RED}Log file preserved at: $parent_dir/$LOG_FILE_NAME${NC}" >&6
        fi
        
        # Restore stdout/stderr to console.
        # We redirect 1->6 and 2->7, but we DO NOT close 6 and 7 yet to avoid
        # "Bad file descriptor" if the shell tries to use them during exit/trap.
        exec 1>&6 2>&7
        
        # Remove directory
        rm -rf "$INSTALL_DIR"
        
        echo -e "${RED}Installation directory '$INSTALL_DIR' has been removed.${NC}"
    fi
    exit "$exit_status"
}

error_handler() {
    local exit_status=$1
    local line_num=$2
    # Only report error if exit status is non-zero (prevents false positives on exit 0)
    if [ "$exit_status" -ne 0 ]; then
        color_err_msg "ERROR: The script failed with status ($exit_status) on line $line_num."
        cleanup_on_error "$exit_status"
    fi
}
# Trap ERR signals
trap 'error_handler $? $LINENO' ERR

confirm_and_delete() {
    local target="$1"
    if [[ "$NON_INTERACTIVE" == true ]]; then
        color_msg "Non-interactive mode: deleting '$target' without prompting."
        rm -rf "$target"
        return
    fi
    local response
    echo -n -e "\n${RED}WARNING:${NC} The directory already exists and will be deleted: ${target}. Are you sure? [y/N] " >&6
    read -r response </dev/tty
    case "$response" in
        [yY][eE][sS] | [yY]) rm -rf "$target" ;;
        *) color_err_msg "Operation cancelled by user. Aborting script."; exit 1 ;;
    esac
}

find_python_cmd() {
    local best_interpreter=""
    local available_interpreters=()

    # Find all available and compatible interpreters
    for interpreter in python3.12 python3.11 python3.10 python3.9 python3 python; do
        # We capture the output in a variable using "|| true" inside the subshell.
        # This prevents the 'command -v' failure (status 1) from triggering the ERR trap.
        local interp_path
        interp_path=$(command -v "$interpreter" 2>/dev/null || true)

        if which "$interpreter" > /dev/null; then
            if "$interpreter" --version 2>&1 | grep -Eq '(Python 3\.9\.|Python 3\.1[0-9]+\.)'; then
                # Store the full path to avoid ambiguity
                available_interpreters+=("$(which "$interpreter")")
                local ver
                ver=$("$interp_path" --version 2>&1 | awk '{print $2}')
                if echo "$ver" | grep -Eq '^3\.(9|[1-9][0-9])\.'; then
                     available_interpreters+=("$interp_path")
                fi
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
    echo "  -b, --branch NAME      The Git branch or tag to clone (default: $TARGET_BRANCH)."
    echo "  -u, --url URL          Direct URL to a ZIP file (DyCoV Source). Overrides --branch."
    echo "  -s, --source-zip FILE  Local ZIP file containing DyCoV source. Overrides --url and --branch."
    echo "  -z, --zipfile FILE     The local name of the Dynawo ZIP file (default: $DYNAWO_ZIP_FILE)."
    echo "  -d, --directory PATH   Directory where the installation will be performed (default: ./dycov)."
    echo "  -y, --yes              Non-interactive mode."
    echo "  -h, --help             Show this help message."
    # We use exit 0 here. This is a clean exit.
    exit 0
}

# Argument parsing
while [[ $# -gt 0 ]]; do
    key="$1"
    case "$key" in
        -b | --branch) TARGET_BRANCH="$2"; shift; shift ;;
        -u | --url) DIRECT_URL="$2"; shift; shift ;;
        -s | --source-zip) 
            # Capture absolute path immediately to avoid issues after 'cd'
            if [[ "$2" = /* ]]; then
                LOCAL_SOURCE_ZIP="$2"
            else
                LOCAL_SOURCE_ZIP="$PWD/$2"
            fi
            shift; shift ;;
        -z | --zipfile) DYNAWO_ZIP_FILE="$2"; CUSTOM_ZIP_USED=true; shift; shift ;;
        -d | --directory) INSTALL_DIR_BASE="$2"; shift; shift ;;
        -y | --yes) NON_INTERACTIVE=true; shift ;;
        -h | --help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

INSTALL_DIR="$INSTALL_DIR_BASE"
TMP_LOCAL_REPO="$INSTALL_DIR/repo_dycov"
DYNAWO_ZIP_URL="$DYNAWO_ZIP_URL_DEFAULT"
LOG="$INSTALL_DIR/$LOG_FILE_NAME"

#######################################
# START OF THE INSTALLATION LOGIC
#######################################

if [ -d "$INSTALL_DIR" ]; then
    echo -e "\n${RED}ERROR: The installation directory already exists: $INSTALL_DIR${NC}" >&6
    confirm_and_delete "$INSTALL_DIR"
fi
mkdir -p "$INSTALL_DIR"

# Redirect stdout (1) and stderr (2) to the log file
# FD 6 is still pointing to the console
exec > "$INSTALL_DIR/$LOG_FILE_NAME"
exec 7>&2
exec 2>&1

color_msg "Step 0: Verifying system dependencies..."
for cmd in curl unzip gcc g++ cmake pdflatex latexmk git awk; do
    if ! command -v "$cmd" > /dev/null; then
        color_err_msg "ERROR: Required command not found: '$cmd'. Please install it."
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

################################################################################
# Download and Extraction of Dynawo
################################################################################
color_msg "Step 1: Downloading and extracting Dynawo..."
cd "$INSTALL_DIR"

if [[ "$NON_INTERACTIVE" == false ]]; then
    echo -n -e "\nDo you want to download and install Dynawo? (Required for some examples) [Y/n] " >&6
    read -r response </dev/tty
    case "$response" in
        [nN][oO] | [nN]) INSTALL_DYNAWO=false; color_msg "Skipping Dynawo installation." ;;
        *) INSTALL_DYNAWO=true; color_msg "Confirmed Dynawo installation." ;;
    esac
else
    color_msg "Non-interactive mode: Installing Dynawo automatically."
fi

if [[ "$INSTALL_DYNAWO" == true ]]; then
    if [[ "$CUSTOM_ZIP_USED" == false ]] && [[ "$TARGET_BRANCH" != "master" ]]; then
        DYNAWO_ZIP_URL="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/$TARGET_BRANCH/$DYNAWO_ZIP_FILE"
    fi

    color_msg "Downloading Dynawo from: $DYNAWO_ZIP_URL"
    curl -O -L --fail "$DYNAWO_ZIP_URL"

    if [[ "$CUSTOM_ZIP_USED" == true ]]; then
        color_msg "NOTICE: Skipping checksum verification for custom ZIP."
    else
        color_msg "Verifying checksum..."
        SHA256SUM_CALCULATED=$(sha256sum "$DYNAWO_ZIP_FILE" | cut -d" " -f1)
        if [ "$SHA256SUM_CALCULATED" != "$DYNAWO_SHA256SUM" ]; then
            color_err_msg "FATAL ERROR: Checksum mismatch. Aborting."
            exit 1
        fi
    fi

    unzip -q "$DYNAWO_ZIP_FILE"
    rm -rf "$DYNAWO_ZIP_FILE"
    color_msg "Dynawo installed."

    # PATCH FOR GCC > 11
    # Use -dumpversion for reliable major version extraction
    GNU_MAJOR=$(g++ -dumpversion | cut -d"." -f1)
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

if [ -n "$LOCAL_SOURCE_ZIP" ]; then
    color_msg "Step 2: Extracting DyCoV source code from local ZIP..."
    
    if [ ! -f "$LOCAL_SOURCE_ZIP" ]; then
        color_err_msg "ERROR: The specified source ZIP file does not exist: $LOCAL_SOURCE_ZIP"
        exit 1
    fi
    
    # Copy file to current dir to avoid issues
    cp "$LOCAL_SOURCE_ZIP" .
    ZIP_FILENAME=$(basename "$LOCAL_SOURCE_ZIP$")
    unzip -q "$ZIP_FILENAME"
    rm -f "$ZIP_FILENAME"

    # Find the extracted directory (ignoring dynawo and virtual envs)
    UNZIPPED_DIR=$(find . -mindepth 1 -maxdepth 1 -type d ! -name 'dynawo' | grep -v 'dycov_venv' | grep -v 'manual')
    if [ -z "$UNZIPPED_DIR" ] || [ "$(echo "$UNZIPPED_DIR" | wc -l)" -ne 1 ]; then
        color_err_msg "ERROR: Could not determine the unzipped source directory. Ensure the zip contains a single root folder."
        exit 1
    fi
    mv "$UNZIPPED_DIR" "$TMP_LOCAL_REPO"

elif [ -n "$DIRECT_URL" ]; then
    color_msg "Step 2: Downloading DyCoV source code from direct URL..."
    SOURCE_ZIP_FILENAME="${DIRECT_URL##*/}"
    curl -L --fail "$DIRECT_URL" -o "$SOURCE_ZIP_FILENAME"
    unzip -q "$SOURCE_ZIP_FILENAME"
    rm -f "$SOURCE_ZIP_FILENAME"

    UNZIPPED_DIR=$(find . -mindepth 1 -maxdepth 1 -type d ! -name 'dynawo' | grep -v 'dycov_venv' | grep -v 'manual')
    if [ -z "$UNZIPPED_DIR" ] || [ "$(echo "$UNZIPPED_DIR" | wc -l)" -ne 1 ]; then
        color_err_msg "ERROR: Could not determine the unzipped source directory."
        exit 1
    fi
    mv "$UNZIPPED_DIR" "$TMP_LOCAL_REPO"

else
    color_msg "Step 2: Shallow-cloning the DyCoV repository (branch/tag: $TARGET_BRANCH)..."
    git clone --depth 1 --branch "$TARGET_BRANCH" "$REPO_URL" "$TMP_LOCAL_REPO"
fi

################################################################################
# Create Virtual Environment and Install
################################################################################
color_msg "Step 3: Creating virtual environment and installing the application..."
if [ -d "${INSTALL_DIR}/$VENV" ]; then
    confirm_and_delete "${INSTALL_DIR}/$VENV"
fi
cd "$INSTALL_DIR"

# 1. Create venv
"$python_cmd" -m venv "$VENV"

# 2. Install uv inside venv
# shellcheck source=/dev/null
. "$VENV"/bin/activate
pip install -q uv

# 3. Install repo using uv
uv pip install -q "$TMP_LOCAL_REPO"
deactivate
color_msg "Virtual environment created."

# Customize the Activation Script
color_msg "Step 4: Customizing the environment activation script..."
ACTIVATE_SCRIPT="$INSTALL_DIR/$VENV/bin/activate"

if [[ "$INSTALL_DYNAWO" == true ]]; then
    ESCAPED_INSTALL_DIR=$(printf '%s\n' "$INSTALL_DIR" | sed -e 's/[]\/$*.^[]/\\&/g')
    USER_PATH="$ESCAPED_INSTALL_DIR/dynawo:\$VIRTUAL_ENV/bin:\$PATH"
else
    USER_PATH="\$VIRTUAL_ENV/bin:\$PATH"
fi

sed -E --in-place=.ORIG -e "s@^PATH=.*@PATH=\"$USER_PATH\"@" "$ACTIVATE_SCRIPT"
cp "$ACTIVATE_SCRIPT" "$INSTALL_DIR"/activate_dycov

# Test
# shellcheck source=/dev/null
. "$INSTALL_DIR"/activate_dycov
echo -e "\n\n--- LIST OF PACKAGES INSTALLED ---"
uv pip list
echo -e "----------------------------------\n\n"
deactivate

################################################################################
# Copy Examples and Build the Manual
################################################################################
color_msg "Step 5: Installing examples and building the manual..."
cp -a "$TMP_LOCAL_REPO"/examples "$INSTALL_DIR"/
# shellcheck source=/dev/null
. "$INSTALL_DIR"/activate_dycov
uv pip install -q sphinx
cd "$TMP_LOCAL_REPO"/docs/manual
make latexpdf > /dev/null 2>&1
make html > /dev/null 2>&1
deactivate
mkdir -p "$INSTALL_DIR"/manual
mv "$TMP_LOCAL_REPO"/docs/manual/build/html "$INSTALL_DIR"/manual/
mv "$TMP_LOCAL_REPO"/docs/manual/build/latex/dycov.pdf "$INSTALL_DIR"/manual/
color_msg "Examples and manuals ready."

################################################################################
# Final Cleanup
################################################################################
rm -rf "$TMP_LOCAL_REPO"

# Restore stdout/stderr to the console (FD 6) and (FD 7)
exec 1>&6 2>&7

# Close the backup FDs
exec 6>&- 7>&-

# We use simple echo because stdout (1) is already back to the console.
echo -e ""
echo -e "${GREEN}INSTALLATION COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}To start using the tool, run: source $INSTALL_DIR/activate_dycov${NC}"
echo -e ""