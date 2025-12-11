#!/bin/bash
#
# start_dycov.sh: the entrypoint for the Dycov tool
# Docker container. It creates the user:group specified when launching
# the container, and then execs a shell as such user.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

# First create the specified user and group
# We use -f to force if they exist (though they shouldn't in a fresh container)
groupadd --force --gid "$dycov_GID" "$dycov_GROUP"
echo "Refreshed/Created group $dycov_GROUP"

# Create user. If UID exists, we might need to handle it, but usually standard approach suffices.
if ! id -u "$dycov_UID" >/dev/null 2>&1; then
    useradd --create-home --home "/home/$dycov_USER" --uid "$dycov_UID" --gid "$dycov_GID" \
            --shell /bin/bash --no-log-init "$dycov_USER"
    echo "CREATED user $dycov_USER"
else
    echo "User UID $dycov_UID already exists, skipping creation."
fi

# Leave the user in an interactive shell
echo -e "\nNow running the Dycov tool under the docker container 'dycov'"
echo -e "To quit the container, just type exit at the command prompt.\n"
exec su - "$dycov_USER"