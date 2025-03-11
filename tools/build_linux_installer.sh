#!/bin/bash
#
# This script automatically builds an installable "*.tar.gz" package of the dycov tool
# for Linux environments. This package provides a mostly self-sufficient install, since
# it bundles as many depemdencies as possible: Dynawo, Python, dycov, and all of its
# dependencies (plus the manual and examples).
#
#
# Requirements for building:
#   * Base OS: Debian 12 or Ubuntu 24.04 LTS, or later.
#   * Have the Dynawo Nightly zip file under the $PWD directory.
#   * Python 3.10 or later available, in order to build the venv.
#
# For end-users of the installer:
#   * Unpack the tar.gz file directly under $HOME
#   * Enable the application with: source dycov/dycov_activate
#   * Note: if you choose a base directory different than $HOME, you'll have to edit
#     paths in dycov/dycov_activate accordingly.
#
#
# (c) Rte 2024
#     Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

# Config vars:
BUILD=$(date +%Y-%m-%d)
BUILD_DIR=$PWD/build
DYNAWO_ZIP=$PWD/Dynawo_omc_v1.7.0.zip
DYNAWO_CHECKSUM=69bec858b6b245ce4bf0b2cd38b2ac8f271c17bb
LOCAL_REPO=$BUILD_DIR/repo_dycov
PKG_DIR=$BUILD_DIR/dycov



# Step 0: Make sure that we have what we need before we start.
if ! which unzip > /dev/null; then
    echo "ERROR: unzip command not found (apt install unzip)"
    exit 1
fi
if [ ! -e "$DYNAWO_ZIP" ]; then
    echo "ERROR: Dynawo zip file not found (need $DYNAWO_ZIP)"
    exit 1
fi
CHECKSUM=$(shasum $PWD/Dynawo_omc_v1.7.0.zip | cut -d" " -f1)
if [ "$CHECKSUM" != "$DYNAWO_CHECKSUM" ]; then
    echo "ERROR: Dynawo ZIP shasum does not match (got $CHECKSUM, expected $DYNAWO_CHECKSUM)"
    exit 1
fi

# This is the same check as in "build_and_install.sh", to catch this error early.
python_cmd=""
for INTERPRETER in python python3 python3.12 python3.11 python3.10 python3.9; do
    if which $INTERPRETER > /dev/null; then
        # But making sure it's really version 3.9 or above: 
        if $INTERPRETER --version | grep -Eq '(Python 3\.9\.|Python 3\.1[0-3].)'; then
            python_cmd="$INTERPRETER"
            break
        fi
    fi
done
if [ "$python_cmd" = "" ]; then
    echo "ERROR: no valid python interpreter found."
    exit 1
fi

echo
echo "Building a dycov installer:"
echo "   * Using $DYNAWO_ZIP"
echo "   * Using Python $($python_cmd --version)"
echo


# Step 1: Create a clean build dir and clone the repo
echo "Building the installer under $BUILD_DIR (removing any previous instance)"
rm -rf "$BUILD_DIR"
mkdir "$BUILD_DIR"
echo "Cloning the git repo"
git clone https://github.com/dynawo/dyn-grid-compliance-verification.git "$LOCAL_REPO"
echo


# Step 2: inside the repo, build and install into the default venv ("dycov_venv")
echo "Executing './build_and_install.sh' inside the local repository"
echo
cd "$LOCAL_REPO"
./build_and_install.sh


# Step 3: create the end-user installation tree, starting with the venv & examples
echo
echo "Copying the venv to $PKG_DIR and customizing the activate script..." 
mkdir "$PKG_DIR"
cp -a "$LOCAL_REPO"/dycov_venv "$PKG_DIR"/
# Customize paths. Note two things: (a) We're assume the user will unpack directly under
# $HOME, otherwise he will have to adjust these two paths; (b) We are adding Dynawo to
# the PATH here as well.
ACTIVATE_SCRIPT="$PKG_DIR"/dycov_venv/bin/activate
USER_VENV="\$HOME/dycov/dycov_venv"
USER_PATH="\$HOME/dycov/dynawo:\$VIRTUAL_ENV/bin:\$PATH"
sed -E --in-place=.ORIG -e "s%^VIRTUAL_ENV=.*%VIRTUAL_ENV=\"$USER_VENV\"%"  \
     -e "s%^PATH=.*%PATH=\"$USER_PATH\"%"  "$ACTIVATE_SCRIPT"
cp "$ACTIVATE_SCRIPT" "$PKG_DIR"/activate_dycov
# Copy the examples too
cp -a "$LOCAL_REPO"/examples "$PKG_DIR"/


# Step 4: Compile the user manual
echo
echo "Compiling the user manual..." 
cd "$LOCAL_REPO"
# shellcheck source=/dev/null
source "$LOCAL_REPO"/dycov_venv/bin/activate
pip install sphinx
cd "$LOCAL_REPO"/docs/manual
make latexpdf
make html
deactivate
mkdir "$PKG_DIR"/manual
mv "$LOCAL_REPO"/docs/manual/build/html "$PKG_DIR"/manual/
mv "$LOCAL_REPO"/docs/manual/build/latex/dycov.pdf "$PKG_DIR"/manual/


# Step 5: unpack Dynawo under the installation tree
echo
echo "Unpacking Dynawo..." 
cd "$PKG_DIR"
unzip -q "$DYNAWO_ZIP"


# Step 6: packing everything
echo
echo "Making the tar.gz file..."
VERSION="v"$(grep  '^version =' "$LOCAL_REPO"/pyproject.toml | cut -d'=' -f 2 | cut -d'"' -f2)
cd "$BUILD_DIR"
tar -zcf dycov_"$VERSION"_"$BUILD".tar.gz dycov/
echo
echo "Done."

