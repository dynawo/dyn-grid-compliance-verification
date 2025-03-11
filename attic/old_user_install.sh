#!/bin/bash
#
# Installation script for end-users:
#   * it uses a venv named "dycov_venv" right under the current directory
#   * it can be used both for first-time installation and for upgrades
#   * it also pip-updates all dependencies to their latest version ("eager" strategy)
# Assumes Python 3.9+.
# 
# (c) 2022--24 RTE
#     Developed by Grupo AIA
#


# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail


PKG="dycov"
LATEST_RELEASE="https://api.github.com/repos/dynawo/dyn-grid-compliance-verification/releases/latest"
SCRIPT_PATH=$(realpath "$0")
MY_PWD=$(dirname "$SCRIPT_PATH")
MY_VENV="$MY_PWD"/dycov_venv
python_cmd=""


GREEN="\\033[1;32m"
NC="\\033[0m"
colormsg()
{
    echo -e "${GREEN}$1${NC}"
}
colormsg_nnl()
{
    echo -n -e "${GREEN}$1${NC}"
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
# getopt-like input option processing
#######################################

# Test for getopt's version (this needs to temporarily deactivate errexit)
set +e
getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
    echo "I'm sorry, 'getopt --test' failed in this environment."
    exit 1
fi
set -e


find_python_cmd
if [ "$python_cmd" = "" ]; then
    echo "ERROR: no valid python interpreter found."
    exit 1
fi


#######################################
# The real meat starts here
#######################################

# Step 0: reminder to refresh your local workspace
echo "You're about to install: $PKG"
read -p "Are you sure? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  exit
fi


# Step 1: make sure the Python venv exists and activate it
echo
if [ ! -d "$MY_VENV" ]; then
    colormsg_nnl "Virtual env not found, creating it now... "
    $python_cmd -m venv "$MY_VENV"
    colormsg "OK."
fi
colormsg_nnl "Activating venv... "
# shellcheck source=/dev/null
source "$MY_VENV"/bin/activate
colormsg "OK."
colormsg "Installing/upgrading pip in the venv... "
pip install --upgrade pip
colormsg "OK."


# Step 2: get the package
echo
colormsg "Download the package... "
curl -s "$LATEST_RELEASE" \
   | grep -E '"browser_download_url"\: ".*\.whl"' \
   | cut -d ':' -f 2,3 \
   | tr -d \" \
   | xargs curl --remote-name


# Step 3: (re)install the package
echo
colormsg "Uninstalling the previous version of the dycov Tool... (if it exists)"
pip uninstall "$PKG"
colormsg "Installing the dycov Tool package and all its dependencies... "
pip install "$MY_PWD"/*.whl


# Step 4: upgrade all deps
echo
colormsg "Upgrading all dependent Python packages to their latest versions... "
pip install --upgrade-strategy eager -U "$PKG"
colormsg "OK."
echo

# Step 6: Clean
echo
colormsg "Cleaning up directories... "
rm -rf -- *.whl
colormsg "OK."
echo

colormsg "INSTALLATION COMPLETE"
colormsg "To use the tool, activate the virtual environment with:"
echo
colormsg"    source dycov/bin/activate"
echo
colormsg "Then, run the command dycov -h to see the available options."
echo
