#!/bin/bash
#
# start_dycov.sh: the entrypoint for the Dycov tool
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

# --- DEFAULTS FOR WSL STANDALONE ---
# If running via Docker, these are injected by run_dycov_docker.sh.
# If running via WSL direct exec, these might be missing, so we default to 1000.
dycov_UID=${dycov_UID:-1000}
dycov_GID=${dycov_GID:-1000}
dycov_USER=${dycov_USER:-"dycov_user"}
dycov_GROUP=${dycov_GROUP:-"dycov_group"}

# First create the specified user and group
groupadd --force --gid "$dycov_GID" "$dycov_GROUP"

# Check if user exists by UID
if ! id -u "$dycov_UID" >/dev/null 2>&1; then
    useradd --create-home --home "/home/$dycov_USER" --uid "$dycov_UID" --gid "$dycov_GID" \
            --shell /bin/bash --no-log-init "$dycov_USER"
    echo "Initialized user $dycov_USER ($dycov_UID)"
else
    # If user exists but name differs, purely cosmetic, but we proceed.
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
echo -e "\n-----------------------------------------------------------"
echo -e " Dycov Container Environment"
echo -e "-----------------------------------------------------------"
echo -e " User:     $dycov_USER ($dycov_UID)"
echo -e " Examples: ~/examples"
echo -e " Type 'exit' to quit."
echo -e "-----------------------------------------------------------\n"

exec su - "$dycov_USER"