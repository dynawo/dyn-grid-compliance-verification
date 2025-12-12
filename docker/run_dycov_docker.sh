#!/bin/bash
#
# run_dycov_docker.sh: A simple wrapper script to launch the Docker
# container for the Dycov tool. It facilitates the
# mapping of the working directory and the user/group to use inside
# the container.
# 
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

# Config vars
DOCKER_IMAGE="dycov:latest"

GREEN="\033[1;32m"
NC="\033[0m"

colormsg()
{
    if [ -t 1 ] ; then
        echo -e "${GREEN}$1${NC}"
    fi
}

usage()
{
    cat <<EOF
Usage: $0 [OPTIONS] WORK_DIR
where WORK_DIR is the host directory that will be mapped to the work directory inside the container.
  Options:
    -u | --user   The host user to "run as" inside the container
    -g | --group  The host group to "run as" inside the container
    -h | --help   This help message
    -d | --debug  Show each execution in this launch script (set -x)
EOF
}

#######################################
# getopt-like input option processing
#######################################

# Test for getopt's version (this needs to temporarily deactivate errexit)
set +e
getopt --test > /dev/null
if [[ $? -ne 4 ]]; then
    echo "I’m sorry, 'getopt --test' failed in this environment."
    exit 1
fi
set -e

OPTIONS=u:g:hd
LONGOPTS=user:,group:,help,debug
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
eval set -- "$PARSED"

# set defaults
user=$(id -u) group=$(id -g) help=n debug=n

while true; do
    case "$1" in
        -u|--user) user="$2"; shift 2 ;;
        -g|--group) group="$2"; shift 2 ;;
        -h|--help) help=y; shift ;;
        -d|--debug) debug=y; shift ;;
        --) shift; break ;;
        *) echo "Programming error"; exit 3 ;;
    esac
done

if [ "$help" = "y" ]; then
    usage
    exit 0
fi

if [ "$debug" = "y" ]; then
    set -x
fi

# handle non-option arguments
if [[ $# -ne 1 ]]; then
    echo
    echo -e "$0: One argument is required (WORK_DIR).\n"
    usage
    exit 4
fi
WORK_DIR=$(realpath "$1")

if [ ! -d "$WORK_DIR" ]; then
   echo "ERROR: work directory $WORK_DIR not found."
   exit 1
fi

#######################################
# Launch Logic
#######################################

# Whoever launches the container, he needs rw permissions on WORK_DIR
MAPPED_DIR=$WORK_DIR/dycov_docker
mkdir -p "$MAPPED_DIR"

# Resolve numeric IDs and Names
dycov_UID=$(id -u "$user")
dycov_GID=$(getent group "$group" | cut -d: -f3)
dycov_USER=$(id -un "$user") 
dycov_GROUP=$(getent group "$group" | cut -d: -f1)

# Ensure the mapped directory is owned by the target user
# Note: This might require sudo if the current user doesn't own WORK_DIR,
# but usually WORK_DIR is inside the user's home.
if [ -w "$MAPPED_DIR" ]; then
    # Only try chown if we are owner or root, otherwise skip to avoid errors
    # (Docker will handle the mapping, but permissions on host might be tricky without this)
    chown "$dycov_UID":"$dycov_GID" "$MAPPED_DIR" 2>/dev/null || true
fi

colormsg "\nLaunching container..."
colormsg "   Host Directory: $MAPPED_DIR"
colormsg "   Mapped to: /home/$dycov_USER inside container"
colormsg "   Running as: $dycov_USER ($dycov_UID:$dycov_GID)\n"

exec docker run --rm -it \
     -v "$MAPPED_DIR":/home/"$dycov_USER" \
     -e dycov_USER="$dycov_USER" -e dycov_GROUP="$dycov_GROUP" -e dycov_UID="$dycov_UID" -e dycov_GID="$dycov_GID" \
     --entrypoint /start_dycov.sh \
     --name dycov --hostname dycov "$DOCKER_IMAGE"