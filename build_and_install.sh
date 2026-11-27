#!/bin/bash
#
# Quick script to automate all steps for building & installing DyCoV from sources.
# Requirements: It just needs 'uv' to be previously installed.
#   * it uses a venv named "dycov_venv"
#   * it installs the dependencies at the versions uv.lock pins
#   * it can install in editable mode and with developer dependencies
# Assumes uv are installed.
# Python 3.13 is installed for the virtual environment.
#
# (c) 2022 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

python_version="3.13"
MY_VENV="$PWD/dycov_venv"

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
    echo "ERROR: 'uv' command not found. Please install it first (see https://docs.astral.sh/uv/getting-started/installation/)."
    exit 1
fi

#######################################
# The real meat starts here
#######################################

colormsg "Step 1: Creating or verifying virtual environment '$MY_VENV'..."
uv venv "$MY_VENV" --python "$python_version"

colormsg "Step 2: Activating environment and installing dependencies..."
# shellcheck source=/dev/null
. "$MY_VENV"/bin/activate

# Build the installation command
extras=()

if [ "$DEVELOPER" = "y" ]; then
    extras+=("dev" "test")
fi

install_target="."
install_extras=""
if [ "$EDITABLE" = "y" ]; then
    install_target="-e ."
fi

if [ ${#extras[@]} -gt 0 ]; then
    install_extras="[$(IFS=,; echo "${extras[*]}")]"
fi

# Install with uv, at the versions uv.lock pins, which the release is tested with
constraints="$(mktemp)"
trap 'rm -f "$constraints"' EXIT
uv export --locked --no-hashes --no-emit-project --all-extras --format requirements-txt \
    --quiet --output-file "$constraints"
uv pip install --upgrade --constraint "$constraints" "$install_target$install_extras"
colormsg "OK."

colormsg "Step 3: Installing the bash completion of the 'dycov' command..."
bash installers/install_bash_completion.sh "$MY_VENV"
colormsg "OK."
echo
colormsg "Development environment is ready."
colormsg "To activate it, run: source $MY_VENV/bin/activate"
echo