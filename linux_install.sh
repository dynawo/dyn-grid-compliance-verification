#!/bin/bash
#
# This script automatically installs the dgcv tool for end-users, on Linux
# environments. It does not need root permissions -- it is designed as a user-level
# install under $HOME.  However, it needs to have some packages available in the system
# such as git, latex, etc. (keep reading below).
#
#
# Requirements for the installation:
#   * Base OS: we recommend Debian 12 / Ubuntu 24.04 LTS, or later. (Debian 11 and
#     Ubuntu 22.04 LTS also work, but they are going to be EOL'ed soon).
#   * All the required OS packages, as listed in the main README.
#
# How it works:
#   * It creates a root dir ("dgcv") under the $PWD. Everything, temporary or permanent, will go in there.
#   * It downloads Dynawo (our own controlled nightly version) and unpacks the zip under $PWD/dgcv/dynawo.
#   * It git-clones the DGCV repo under a temporary subdir, $PWD/dgcv/repo_dgcv.
#   * It builds & installs the app (and all of its Python dependencies) in a venv, under $PWD/dgcv/dgcv_venv.
#     (Note: it also edits the venv activation script to make sure this Dynawo is the first in the $PATH).
#   * It copies the examples under $PWD/dgcv/examples.
#   * It also builds the User Manual and leaves it under $PWD/dgcv/user_manual.
#   * It deletes the temporarily cloned repo.
#   * The tool is then ready to be used, by sourcing $PWD/dgcv/activate_dgcv
#
# Why we do it this way:
#   * Publishing our own wheels would avoid git-cloning and building, but on the other
#     hand there's a risk that our compiled pip packages are not compatible with the
#     user's version of Python. Additionally, we would also have to publish separate zip
#     packages for the examples and the manuals.
#   * Instead, going the git-clone route simplifies both this installation script *and* the
#     process of releasing new versions, since we only need to release two things:
#     Dynawo, and this install script.
#
#
# (c) Rte 2024
#     Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

# Configuration vars that depend on the release:
RELEASE_TAG="v0.5.2"
DYNAWO_ZIP_FILE="Dynawo_omc_v1.7.0.zip"
DYNAWO_CHECKSUM="69bec858b6b245ce4bf0b2cd38b2ac8f271c17bb"
###TODO: RESTORE THIS LINE WHEN GONE PUBLIC
#DYNAWO_ZIP_URL="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download/$RELEASE_TAG/$DYNAWO_ZIP_FILE"
DYNAWO_ZIP_URL="https://github.com/dynawo/dynawo/releases/download/nightly/$DYNAWO_ZIP_FILE"
# The configurable section ends here, you shouldn't need to edit the rest.

REPO_URL="https://github.com/dynawo/dyn-grid-compliance-verification.git"
INSTALL_DIR=$PWD/dgcv
TMP_LOCAL_REPO=$INSTALL_DIR/repo_dgcv
VENV="dgcv_venv"
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG=$INSTALL_DIR/installation_$DATETIME.log



# Some useful functions
RED="\\033[1;31m"  # ANSI color escape sequences
GREEN="\\033[1;32m"
NC="\\033[0m"
color_msg()
{
    echo -e "$(date '+%Y-%m-%d %H:%M%S'): $1"  # to the log file, no color, timestamped
    echo -e "${GREEN}$1${NC}" >&6              # to the console, in color
}

color_msg_nnl()
{
    echo -e "$(date '+%Y-%m-%d %H:%M%S'): $1"  # to the log file, no color, timestamped
    echo -n -e "${GREEN}$1${NC}" >&6           # to the console, in color
}

color_err_msg()
{
    echo -e "$(date '+%Y-%m-%d %H:%M%S'): $1"  # to the log file, no color, timestamped
    echo -e "\n\n${RED}$1${NC}" >&6            # to the console, in color
}

# Since we'll redirect stdout & stderr to a log, set up a handler to show errors on the console too: 
trap 'error_handler $? $LINENO' ERR
error_handler()
{
    color_err_msg "ERROR: exit status ($1) occurred on Line $2. Check the installation log for details."
}

find_python_cmd()
{
    # PEP394-compliant environments should define "python" or "python3", but here we will be
    # permissive; we'll use the first Python found from this list:
    for INTERPRETER in python python3 python3.12 python3.11 python3.10 python3.9; do
        if which $INTERPRETER > /dev/null; then
            # But making sure it's version 3.9 or above: 
            if $INTERPRETER --version | grep -Eq '(Python 3\.9\.|Python 3\.1[0-3].)'; then
                python_cmd="$INTERPRETER"
                break
            fi
        fi
    done
}



#######################################
# The real meat starts here
#######################################
# We will only allow installation on a fresh, clean directory
if [ -d "$INSTALL_DIR" ]; then
    # we can't call color_err_msg yet, since the $LOG and stderr redirect cannot be executed yet
    echo -e "\n\n${RED}ERROR: installation directory already exists: $INSTALL_DIR${NC}\n"
    exit 1
fi
mkdir "$INSTALL_DIR"

# Set up redirections to the log file
exec 6>&1      # Link file descriptor #6 with stdout. Saves stdout.
exec >"$LOG"   # stdout redirected to the log file
exec 7>&2      # Link file descriptor #7 with stderr. Saves stderr.
exec 2>&1      # stderr redirected to stdout
# Reminder of how to restore stderr and stdout in case you need it elsewhere in the script:
#exec 1>&6 6>&-    # Restore stdout and close fd 6
#exec 2>&7 7>&-    # Restore stderr and close fd 7



######################################################################
# Step 0: make sure that we have everything we need before we start.
######################################################################
for needed_command in curl unzip git; do
    if ! which "$needed_command" > /dev/null; then
	color_err_msg "ERROR: $needed_command command not found (sudo apt install $needed_command?)"
	exit 1
    fi
done
# This is the same check as in "build_and_install.sh", to catch this error early.
python_cmd=""
find_python_cmd
if [ "$python_cmd" = "" ]; then
    color_err_msg "ERROR: no valid python interpreter found."
    exit 1
fi

color_msg ""
color_msg "Beginning the installation of the dgcv tool under: $INSTALL_DIR"
color_msg "   * Base Python version is $($python_cmd --version), python command is: \"$python_cmd\""
color_msg "   * The installation will download ~900 MB, use up to ~2.2GB, and end up taking ~1.6 GB of disk space"
color_msg "   * To view the progress of the installation in detail, open another term and execute:"
color_msg "        tail -f $LOG"
color_msg ""



#####################################################################
# Step 1: download Dynawo and unpack under the installation tree
#####################################################################
color_msg ""
color_msg_nnl "Downloading Dynawo from the dgcv repository (~ 150 MB)... "
cd "$INSTALL_DIR"
curl -O -L --fail "$DYNAWO_ZIP_URL"
CHECKSUM=$(shasum "$DYNAWO_ZIP_FILE" | cut -d" " -f1)
###TODO: REMOVE THIS LINE WHEN GONE PUBLIC
CHECKSUM=$DYNAWO_CHECKSUM
if [ "$CHECKSUM" != "$DYNAWO_CHECKSUM" ]; then
    color_err_msg "ERROR: Dynawo ZIP shasum does not match (got $CHECKSUM, expected $DYNAWO_CHECKSUM)"
    exit 1
fi
unzip -q "$DYNAWO_ZIP_FILE" && rm "$DYNAWO_ZIP_FILE" 
color_msg "Dynawo downloaded & installed OK."



##################################################################################
# Step 2: git-clone the repo under a temporary subdir inside $PWD/dgcv/.
##################################################################################
color_msg ""
color_msg_nnl "Cloning the git repo (shallow clone of tag \"$RELEASE_TAG\", this will take ~ 1 min)... "
rm -rf "$TMP_LOCAL_REPO"
git clone --depth 1 --branch "$RELEASE_TAG" "$REPO_URL" "$TMP_LOCAL_REPO"
color_msg "repo cloned OK."



##################################################################################
# Step 3: build & install the app in a venv under $PWD/dgcv/dgcv_venv/.
##################################################################################
color_msg ""
color_msg_nnl "Building and installing to a fresh venv (this will take ~ 30 to 60 sec)... "
rm -rf "${INSTALL_DIR:?}/$VENV"
cd "$INSTALL_DIR"
"$TMP_LOCAL_REPO"/build_and_install.sh
color_msg "build_and_install.sh completed OK."



#########################################################
# Step 4: customize the venv activate script.
#########################################################
# The original activate script defines PATH="$VIRTUAL_ENV/bin:$PATH"
# Here we insert the PATH to our version of Dynawo (installed later below).
color_msg ""
color_msg_nnl "Customize the venv 'activate' script... "
ACTIVATE_SCRIPT="$INSTALL_DIR/$VENV"/bin/activate
USER_PATH="$INSTALL_DIR/dynawo:\$VIRTUAL_ENV/bin:\$PATH"
sed -E --in-place=.ORIG -e "s%^PATH=.*%PATH=\"$USER_PATH\"%"  "$ACTIVATE_SCRIPT"
cp "$ACTIVATE_SCRIPT" "$INSTALL_DIR"/activate_dgcv
# Also leave a trace of the package versions installed by pip
# shellcheck source=/dev/null
source "$INSTALL_DIR"/activate_dgcv
echo -e "\n\nLIST OF INSTALLED PACKAGES IN THE VENV:"
pip list
echo -e "------------------------------------------------\n\n"
deactivate
color_msg "activation script customized OK."



#########################################################
# Step 5: copy the examples and build the User Manual
#########################################################
color_msg ""
color_msg_nnl "Copy the examples and build the User Manual... "
cp -a "$TMP_LOCAL_REPO"/examples "$INSTALL_DIR"/
# shellcheck source=/dev/null
source "$INSTALL_DIR"/activate_dgcv
pip install sphinx
cd "$TMP_LOCAL_REPO"/docs/manual
make latexpdf
make html
deactivate
mkdir "$INSTALL_DIR"/manual
mv "$TMP_LOCAL_REPO"/docs/manual/build/html "$INSTALL_DIR"/manual/
mv "$TMP_LOCAL_REPO"/docs/manual/build/latex/dgcv.pdf "$INSTALL_DIR"/manual/
color_msg "examples and manuals installed OK."



#########################################################
# Step 6: clean up
#########################################################
color_msg ""
color_msg_nnl "Cleaning up... "
rm -rf "$TMP_LOCAL_REPO"
color_msg "OK."
color_msg ""

