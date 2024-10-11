#!/bin/bash
#
#
# start_dgcv.sh: the entrypoint for the Dynamic Grid Compliance Verification tool
# Docker container. It creates the user:group specified when launching
# the container, and then execs a shell as such user.
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

# First create the specified user and group
groupadd --gid "$DGCV_GID" "$DGCV_GROUP"
echo "CREATED group $DGCV_GROUP"
useradd --create-home --home "/home/$DGCV_USER" --uid "$DGCV_UID" --gid "$DGCV_GID" \
        --shell /bin/bash --no-log-init "$DGCV_USER"
echo "CREATED user $DGCV_USER"


# Leave the user in an interactive shell
echo -e "\nNow running the Dynamic Grid Compliance Verification tool under the docker container 'dgcv'"
echo -e "To quit the container, just type exit at the command prompt.\n"
exec su - "$DGCV_USER"

