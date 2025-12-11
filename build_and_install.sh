#!/bin/bash
#
# Quick script to automate all steps for building/installing the package using 'uv'.
#   * it uses a venv named "dycov_venv"
#   * it also pip-updates all dependencies to their latest version
#   * it can install in editable mode and with developer dependencies
# Assumes Python 3.9 or later and uv are installed.
#
# (c) 2022 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

MY_VENV="$PWD/dycov_venv"
python_cmd=""

GREEN="\033[1;32m"
NC="\033[0m"
colormsg() {
    local msg="$1"
    echo -e "${GREEN}${msg}${NC}"
}

show_usage() {
    cat <<EOF
Usage: $0 [OPTIONS]
  Options:
    -e | --editable   Install the tool as an editable package (for developers)
    -d | --devel      Install additional Python packages for developers (ruff, etc.)
    -h | --help       Show this help message
EOF
}

# Searches for the newest compatible Python interpreter (3.9+).
find_python_cmd() {
    local best_interpreter=""
    local -a available_interpreters=() # Use local array for safety

    # Find all available and compatible interpreters
    for interpreter in python3.12 python3.11 python3.10 python3.9 python3 python; do
        if command -v "$interpreter" > /dev/null; then
            # Check version with a single command to stdout and grep for 3.9+
            if "$interpreter" -c 'import sys; exit(sys.version_info >= (3, 9))' 2>/dev/null; then
                # Store the full path to avoid ambiguity
                available_interpreters+=("$(command -v "$interpreter")")
            fi
        fi
    done

    # If we found any, sort them by version and pick the best one.
    if [ ${#available_interpreters[@]} -gt 0 ]; then
        # Get unique paths, get versions, sort, and extract the path of the newest one
        best_interpreter=$(printf "%s\n" "${available_interpreters[@]}" | sort -u | while read -r interp; do
            # Extract major.minor.patch version string
            local version
            version=$("$interp" --version 2>&1 | awk '{print $2}')
            echo "$version $interp"
        done | sort -V -r | head -n 1 | awk '{print $2}')
    fi

    # Set the global variable
    python_cmd="$best_interpreter"
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
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
eval set -- "$PARSED"

EDITABLE=n
DEVELOPER=n
HELP=n
while true; do
    case "$1" in
        -e|--editable) EDITABLE=y; shift ;;
        -d|--devel) DEVELOPER=y; shift ;;
        -h|--help) HELP=y; shift ;;
        --) shift; break ;;
        *) echo "Programming error"; exit 3 ;;
    esac
done

if [ "$HELP" = "y" ]; then
    show_usage
    exit 0
fi

# Check for uv using command -v
if ! command -v uv &> /dev/null; then
    echo "ERROR: 'uv' command not found. Please install it first (e.g., 'pip install uv')."
    exit 1
fi

find_python_cmd
if [ -z "$python_cmd" ]; then
    echo "ERROR: no valid python interpreter found (3.9+ required)."
    exit 1
fi

#######################################
# The real meat starts here
#######################################

colormsg "Step 1: Creating or verifying virtual environment '$MY_VENV'..."
uv venv "$MY_VENV" --python "$python_cmd"

colormsg "Step 2: Activating environment and installing dependencies..."
# shellcheck source=/dev/null
. "$MY_VENV"/bin/activate

# Build the installation command
install_target="."
install_extras=""

if [ "$EDITABLE" = "y" ]; then
    install_target="-e ."
fi

if [ "$DEVELOPER" = "y" ]; then
    # These extras are defined in pyproject.toml
    install_extras="[dev,test]"
fi

# Install with uv, ensuring proper quoting
uv pip install --upgrade "$install_target$install_extras"
colormsg "OK."
echo
colormsg "Development environment is ready."
colormsg "To activate it, run: . $MY_VENV/bin/activate"
echo