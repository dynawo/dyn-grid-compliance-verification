#!/bin/bash
#
# start_dycov.sh: the entrypoint for the Dycov tool (GFM-only)
# Docker container.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

# First create the specified user and group
groupadd --force --gid "$dycov_GID" "$dycov_GROUP"
echo "Refreshed/Created group $dycov_GROUP"

if ! id -u "$dycov_UID" >/dev/null 2>&1; then
    useradd --create-home --home "/home/$dycov_USER" --uid "$dycov_UID" --gid "$dycov_GID" \
            --shell /bin/bash --no-log-init "$dycov_USER"
    echo "CREATED user $dycov_USER"
else
    echo "User UID $dycov_UID already exists, skipping creation."
fi

# Copy examples to user home so they are writable and ready to use
USER_HOME="/home/$dycov_USER"
if [ -d "/opt/dycov/examples" ] && [ ! -d "$USER_HOME/examples" ]; then
    echo "Copying examples to $USER_HOME/examples..."
    cp -r /opt/dycov/examples "$USER_HOME/"
    chown -R "$dycov_UID":"$dycov_GID" "$USER_HOME/examples"
fi

# Leave the user in an interactive shell
echo -e "\nNow running the Dycov tool (GFM-only) under the docker container"
echo -e "Examples are available in ~/examples"
echo -e "To quit the container, just type exit at the command prompt.\n"
exec su - "$dycov_USER"