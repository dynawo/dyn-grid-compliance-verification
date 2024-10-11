#!/bin/bash
#
# Quick and dirty script to automate all steps for building/installing the package:
#   * it uses a venv named "dgcv_venv" (created under the $PWD when you invoke it)
#   * it also pip-updates all dependencies to their latest version ("eager" strategy)
# Assumes Python 3.9 or later.
# 
# (c) 2022 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail


PKG="dgcv"
SCRIPT_PATH=$(realpath "$0")
MY_LOCAL_REPO=$(dirname "$SCRIPT_PATH")
MY_VENV="$PWD"/dgcv_venv
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

show_usage()
{
    cat <<EOF
Usage: $0 [OPTIONS]
  Options:
    -e | --editable   Install the tool as an editable package (for developers)
    -d | --devel      Install additional Python packages for developers (adds ~250 MB to the venv)
    -h | --help       Show this help message
EOF
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

OPTIONS=edh
LONGOPTS=editable,devel,help
# -activate quoting/enhanced mode (e.g. by writing out “--options”)
# -pass arguments only via   -- "$@"   to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"
# now enjoy the options in order and nicely split until we see "--"
# defaults:
EDITABLE=n DEVELOPER=n HELP=n
while true; do
    case "$1" in
        -e|--editable)
            EDITABLE=y
            shift
            ;;
        -d|--devel)
            DEVELOPER=y
            shift
            ;;
        -h|--help)
            HELP=y
            shift
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Programming error"
            exit 3
            ;;
    esac
done

if [ "$HELP" = "y" ]; then
    show_usage
    exit 0
fi


find_python_cmd
if [ "$python_cmd" = "" ]; then
    echo "ERROR: no valid python interpreter found."
    exit 1
fi


#######################################
# The real meat starts here
#######################################

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
colormsg "Installing/upgrading pip & build in the venv... "
pip install --upgrade pip build
colormsg "OK."


# Step 2: build
echo
colormsg "Building the DGCV Tool package... "
if [ $EDITABLE = "y" ]; then
    colormsg "   SKIPPING (installing the DGCV Tool as an editable Python package)."
else
    cd "$MY_LOCAL_REPO" && rm -rf build dist && python -m build --wheel
    colormsg "OK."
fi


# Step 3: install the package
echo
colormsg "Uninstalling the previous version of the DGCV Tool... (if it exists)"
pip uninstall "$PKG"
colormsg "Installing the DGCV Tool package and all its dependencies... "
if [ $EDITABLE = "y" ]; then
    cd "$MY_LOCAL_REPO" && pip install -e .
else
    pip install "$MY_LOCAL_REPO"/dist/*.whl
fi


# Step 4: upgrade all deps
echo
colormsg "Upgrading all dependent Python packages to their latest versions... "
pip install --upgrade-strategy eager -U "$PKG"
colormsg "OK."
echo


# Step 5 (OPTIONAL): install additional packages used only by developers
if [ $DEVELOPER = "y" ]; then
    echo
    colormsg "Installing additional Python packages for developers... "
    pip install --upgrade-strategy eager -U pipdeptree black isort flake8 pytest sphinx jupyter
    colormsg "OK."
    echo
fi

# Step 6: Clean
echo
colormsg "Cleaning up build directories... "
rm -rf build dist
colormsg "OK."
echo
