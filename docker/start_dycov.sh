#!/bin/bash
#
#
# start_dycov.sh: the entrypoint for the Dycov tool
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
groupadd --gid "$dycov_GID" "$dycov_GROUP"
echo "CREATED group $dycov_GROUP"
useradd --create-home --home "/home/$dycov_USER" --uid "$dycov_UID" --gid "$dycov_GID" \
        --shell /bin/bash --no-log-init "$dycov_USER"
echo "CREATED user $dycov_USER"


# Leave the user in an interactive shell
echo -e "\nNow running the Dycov tool under the docker container 'dycov'"
echo -e "To quit the container, just type exit at the command prompt.\n"
exec su - "$dycov_USER"