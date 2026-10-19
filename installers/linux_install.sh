
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
#   * Downloads the examples (their curves ship with the release, not with the sources)
#     and builds the manual.
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

# Python version requirements
python_cmd="3.13"

# The release to install. Empty means the latest one, which is what an end user wants and
# what the copy published with a release overrides with its own tag.
TARGET_RELEASE=""
RELEASES_API="https://api.github.com/repos/dynawo/dyn-grid-compliance-verification/releases/latest"
# A branch instead of the release's tag, for someone testing sources that are not released yet.
# The assets still come from a release: a branch has no release and no assets of its own.
TARGET_BRANCH=""
REPO_URL="https://github.com/dynawo/dyn-grid-compliance-verification.git"
DYNAWO_SHA256SUM="fbba80aa7ac6a990928b601e339a43ec49d538b956c97a51d038d1dcdea48768"

DYNAWO_ZIP_FILE="Dynawo_omc_v1.8.0.zip"

# The examples are an asset of the release too: their curves are not in the repository, so a
# clone of the sources carries the examples without them. The checksum below is written by
# installers/prepare_release.sh into the copy published with each release.
EXAMPLES_ZIP_FILE="dycov_examples.zip"
EXAMPLES_SHA256SUM=""

# Script State Variables
INSTALL_DIR_BASE="$PWD/dycov"
NON_INTERACTIVE=false
CUSTOM_ZIP_USED=false
DIRECT_URL=""
LOCAL_SOURCE_ZIP=""
LOCAL_EXAMPLES_ZIP=""
INSTALL_DYNAWO=true

# Local paths
INSTALL_DIR="$INSTALL_DIR_BASE"
TMP_LOCAL_REPO="$INSTALL_DIR/repo_dycov"
VENV="dycov_venv"
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG_FILE_NAME="installation_$DATETIME.log"

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

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -r, --release TAG      The release to install (default: the latest one)."
    echo "  -b, --branch NAME      Clone the sources from this branch instead of the"
    echo "                         release's tag; its assets still come from the release."
    echo "  -u, --url URL          Direct URL to a ZIP file (DyCoV Source). Overrides --branch."
    echo "  -s, --source-zip FILE  Local ZIP file containing DyCoV source. Overrides --url and --branch."
    echo "  -z, --zipfile FILE     The local name of the Dynawo ZIP file (default: $DYNAWO_ZIP_FILE)."
    echo "  -x, --examples-zip FILE  Local ZIP with the examples (default: the asset of the release)."
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
        -r | --release) TARGET_RELEASE="$2"; shift; shift ;;
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
        -x | --examples-zip)
            # Capture absolute path immediately to avoid issues after 'cd'
            if [[ "$2" = /* ]]; then
                LOCAL_EXAMPLES_ZIP="$2"
            else
                LOCAL_EXAMPLES_ZIP="$PWD/$2"
            fi
            shift; shift ;;
        -d | --directory) INSTALL_DIR_BASE="$2"; shift; shift ;;
        -y | --yes) NON_INTERACTIVE=true; shift ;;
        -h | --help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

INSTALL_DIR="$INSTALL_DIR_BASE"
TMP_LOCAL_REPO="$INSTALL_DIR/repo_dycov"

# What is installed is a release. Its tag names the sources to clone and the assets to download,
# and a branch only replaces the first of the two.
if [ -z "$TARGET_RELEASE" ]; then
    TARGET_RELEASE=$(curl -sS -L --fail "$RELEASES_API" 2> /dev/null |
        sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1)
    if [ -z "$TARGET_RELEASE" ]; then
        echo -e "\n${RED}ERROR: could not find out the latest release. Name one with --release.${NC}"
        exit 1
    fi
fi
SOURCE_REF="${TARGET_BRANCH:-$TARGET_RELEASE}"
RELEASE_URL="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/$TARGET_RELEASE"
DYNAWO_ZIP_URL="$RELEASE_URL/$DYNAWO_ZIP_FILE"
EXAMPLES_ZIP_URL="$RELEASE_URL/$EXAMPLES_ZIP_FILE"
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
for cmd in curl unzip make pdflatex latexmk dvisvgm git awk uv sha256sum; do
    if ! command -v "$cmd" > /dev/null; then
        color_err_msg "ERROR: Required command not found: '$cmd'. Please install it."
        exit 1
    fi
done

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
    ZIP_FILENAME=$(basename "$LOCAL_SOURCE_ZIP")
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
    color_msg "Step 2: Shallow-cloning the DyCoV repository ($SOURCE_REF)..."
    git clone --progress --depth 1 --single-branch --branch "$SOURCE_REF" "$REPO_URL" "$TMP_LOCAL_REPO"
    cd "$TMP_LOCAL_REPO"
    git fetch --depth 1 --tags --progress
fi

################################################################################
# Create Virtual Environment and Install
################################################################################
color_msg "Step 3: Creating virtual environment and installing the application..."
# Check for uv using command -v
if [ -d "${INSTALL_DIR}/$VENV" ]; then
    confirm_and_delete "${INSTALL_DIR}/$VENV"
fi
cd "$INSTALL_DIR"

# 1. Create venv
uv venv "$VENV" --python "$python_cmd"

# 2. Install repo using uv
. "$VENV"/bin/activate
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
bash "$TMP_LOCAL_REPO"/installers/install_bash_completion.sh "$INSTALL_DIR/$VENV"
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
color_msg "Step 5: Installing examples, tutorials and building the manual..."
# The examples come from the release, not from the sources: their curve directories are not
# versioned, so a clone of the sources holds an examples tree without them.
cd "$INSTALL_DIR"
if [ -n "$LOCAL_EXAMPLES_ZIP" ]; then
    color_msg "Taking the examples from: $LOCAL_EXAMPLES_ZIP"
    if [ ! -f "$LOCAL_EXAMPLES_ZIP" ]; then
        color_err_msg "ERROR: The specified examples ZIP file does not exist: $LOCAL_EXAMPLES_ZIP"
        exit 1
    fi
    cp "$LOCAL_EXAMPLES_ZIP" "$EXAMPLES_ZIP_FILE"
    color_msg "NOTICE: Skipping checksum verification for local examples ZIP."
else
    if [ -z "$EXAMPLES_SHA256SUM" ]; then
        color_err_msg "FATAL ERROR: this installer pins no examples archive. Use the
linux_install.sh published with a release, which carries the checksum of its
$EXAMPLES_ZIP_FILE, or pass one with --examples-zip. Aborting."
        exit 1
    fi

    color_msg "Downloading the examples from: $EXAMPLES_ZIP_URL"
    curl -O -L --fail "$EXAMPLES_ZIP_URL"

    color_msg "Verifying checksum..."
    SHA256SUM_CALCULATED=$(sha256sum "$EXAMPLES_ZIP_FILE" | cut -d" " -f1)
    if [ "$SHA256SUM_CALCULATED" != "$EXAMPLES_SHA256SUM" ]; then
        color_err_msg "FATAL ERROR: Checksum mismatch for $EXAMPLES_ZIP_FILE. Aborting."
        exit 1
    fi
fi

unzip -q "$EXAMPLES_ZIP_FILE"
rm -f "$EXAMPLES_ZIP_FILE"
# Blank workbooks to describe an installation in, one per standard.
cp -a "$TMP_LOCAL_REPO"/workbooks "$INSTALL_DIR"/
# User-facing tutorials and installation guides (only the *.md files, so their
# relative cross-links work: tutorials/README.md links to ../installation/).
# Build helpers (md2pdf.sh, listings-setup.tex) are not installed.
mkdir -p "$INSTALL_DIR"/tutorials "$INSTALL_DIR"/installation
cp -a "$TMP_LOCAL_REPO"/docs/tutorials/*.md "$INSTALL_DIR"/tutorials/
cp -a "$TMP_LOCAL_REPO"/docs/installation/*.md "$INSTALL_DIR"/installation/
# shellcheck source=/dev/null
. "$INSTALL_DIR"/activate_dycov
uv pip install -q sphinx
cd "$TMP_LOCAL_REPO"/docs/manual
# The installation log already collects their output. Their stdin is closed
# because the documentation pipes this script into bash, and a child reading
# it would swallow the rest of the installer.
make latexpdf < /dev/null
make html < /dev/null
deactivate
mkdir -p "$INSTALL_DIR"/manual
mv "$TMP_LOCAL_REPO"/docs/manual/build/html "$INSTALL_DIR"/manual/
mv "$TMP_LOCAL_REPO"/docs/manual/build/latex/dycov.pdf "$INSTALL_DIR"/manual/
color_msg "Examples, tutorials and manuals ready."

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
echo -e "${GREEN}Examples: $INSTALL_DIR/examples  |  Workbooks: $INSTALL_DIR/workbooks  |  Tutorials: $INSTALL_DIR/tutorials  |  Manual: $INSTALL_DIR/manual${NC}"
echo -e ""
