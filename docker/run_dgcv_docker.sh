#!/bin/bash
#
# run_dycov_docker.sh: A simple wrapper script to launch the Docker
# container for the Dynamic grid Compliance Verification tool. It facilitates the
# mapping of the working directory and the user/group to use inside
# the container.
# 
# Example for running it as your current user under your directory "mywork":
#
#    $ ./run_dycov_docker.sh $HOME/mywork
#
# and then $HOME/mywork will be mapped to just $HOME/ when inside the
# container; the resulting files will be owned by your user UID and
# your effective group GID.
#
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     demiguelm@aia.es
#     omsg@aia.es
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

# Config vars
DOCKER_IMAGE="dycov:latest"


# Nothing else to configure below this point
GREEN="\\033[1;32m"
NC="\\033[0m"

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
    -g | --group  The host user to "run as" inside the container
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
# Invoke getopt:
#   * activate quoting/enhanced mode (e.g. by writing out “--options”)
#   * pass arguments only via  -- "$@"  to separate them correctly
PARSED=$(getopt --options=$OPTIONS --longoptions=$LONGOPTS --name "$0" -- "$@")
# read getopt’s output this way to handle the quoting right:
eval set -- "$PARSED"

# set defaults
user=$(id -u) group=$(id -g) help=n debug=n
# now enjoy the options in order and nicely split until we see --
while true; do
    case "$1" in
        -u|--user)
            user="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
            ;;
        -g|--group)
            group="$2"   # it could contain whitespace, so remember to quote it!
            shift 2
            ;;
        -h|--help)
            help=y
            shift
            ;;
        -d|--debug)
            debug=y
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

if [ $help = "y" ]; then
    usage
    exit 0
fi

if [ $debug = "y" ]; then
    set -x
fi

# handle non-option arguments
if [[ $# -ne 1 ]]; then
    echo
    echo -e "$0: One argument is required.\n"
    usage
    exit 4
fi
WORK_DIR=$(realpath "$1")

if [ ! -d "$WORK_DIR" ]; then
   echo "ERROR: work directory $WORK_DIR not found."
   exit 1
fi



#######################################
# The real meat starts here
#######################################

# Whoever launches the container, he needs rw permissions on WORK_DIR
MAPPED_DIR=$WORK_DIR/dycov_docker
mkdir -p "$MAPPED_DIR"
dycov_UID=$(id -u "$user")
dycov_GID=$(getent group "$group" | cut -d: -f3)
dycov_USER=$(id -un "$user")  # because $user may be numeric
dycov_GROUP=$(getent group "$group" | cut -d: -f1)  # because $group may be numeric
chown "$dycov_UID":"$dycov_GID" "$MAPPED_DIR"

colormsg "\nLaunching container."
colormsg "   Files will be generated under: $MAPPED_DIR"
colormsg "   Files will be owned by $dycov_UID:$dycov_GID\n\n"
exec docker run --rm -it \
     -v "$MAPPED_DIR":/home/"$dycov_USER" \
     -e dycov_USER="$dycov_USER" -e dycov_GROUP="$dycov_GROUP" -e dycov_UID="$dycov_UID" -e dycov_GID="$dycov_GID" \
     --entrypoint /start_dycov.sh \
     --name dycov --hostname dycov "$DOCKER_IMAGE"

