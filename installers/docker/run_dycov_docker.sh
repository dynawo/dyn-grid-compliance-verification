#!/bin/bash
#
# run_dycov_docker.sh: Wrapper to launch the Dycov container.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

set -o nounset -o noclobber
set -o errexit -o pipefail 

# Config vars
DOCKER_IMAGE="dycov:latest"

GREEN="\033[1;32m"
NC="\033[0m"

colormsg() {
    if [ -t 1 ] ; then
        echo -e "${GREEN}$1${NC}"
    fi
}

usage() {
    cat <<EOF
Usage: $0 [OPTIONS] WORK_DIR
where WORK_DIR is the host directory that will be mapped to the work directory inside the container.
  Options:
    -u | --user   The host user ID to "run as" inside the container
    -g | --group  The host group ID to "run as" inside the container
    -h | --help   This help message
EOF
}

# --- Argument Parsing ---
# (Simple parsing to avoid getopt dependency issues on some minimal environments)

if [ -n "${SUDO_UID:-}" ]; then
    user="$SUDO_UID"
    group="$SUDO_GID"
else
    user=$(id -u)
    group=$(id -g)
fi

WORK_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--user)
            user="$2"; shift 2 ;;
        -g|--group)
            group="$2"; shift 2 ;;
        -h|--help)
            usage; exit 0 ;;
        -*)
            echo "Unknown option $1"; usage; exit 1 ;;
        *)
            if [ -z "$WORK_DIR" ]; then
                WORK_DIR="$1"
            else
                echo "Error: Multiple work directories specified."
                usage; exit 1
            fi
            shift ;;
    esac
done

if [ -z "$WORK_DIR" ]; then
    echo "Error: WORK_DIR argument is required."
    usage
    exit 1
fi

WORK_DIR=$(realpath "$WORK_DIR")

if [ ! -d "$WORK_DIR" ]; then
   echo "ERROR: work directory $WORK_DIR not found."
   exit 1
fi

# --- Launch Logic ---

# Resolve Names for display
dycov_USER=$(id -un "$user" 2>/dev/null || echo "user_$user") 

colormsg "\nLaunching Dycov container..."
colormsg "   Host Directory: $WORK_DIR"
colormsg "   Running as: $dycov_USER ($user:$group)"

# We pass the host UID/GID as environment variables.
# The internal /start_dycov.sh script (inside the image) uses these to
# create a matching user on the fly.
exec docker run --rm -it \
     -v "$WORK_DIR":/home/"$dycov_USER" \
     -w /home/"$dycov_USER" \
     -e dycov_USER="$dycov_USER" \
     -e dycov_UID="$user" \
     -e dycov_GID="$group" \
     -e dycov_GROUP=$(id -g) \
     "$DOCKER_IMAGE"