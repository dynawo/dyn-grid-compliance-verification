#!/bin/bash
#
# import_image.sh: Re-creates the Dycov Docker image from the flat filesystem (.tar.gz).
#
# CRITICAL: Since the source file was created via 'docker export' (for WSL support),
# it lacks Docker metadata (ENV, ENTRYPOINT). This script restores them during import.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

set -o nounset -o noclobber
set -o errexit -o pipefail 

INPUT_FILE="dycov_dist.tar.gz"
TARGET_IMAGE="dycov:latest"

GREEN="\033[1;32m"
RED="\033[1;31m"
NC="\033[0m"

colormsg() {
    echo -e "${GREEN}$1${NC}"
}

errormsg() {
    echo -e "${RED}$1${NC}" >&2
}

# Allow passing a different file as argument
if [ "$#" -ge 1 ]; then
    INPUT_FILE="$1"
fi

if [ ! -f "$INPUT_FILE" ]; then
    errormsg "ERROR: File '$INPUT_FILE' not found."
    errormsg "Usage: $0 [path_to_tar_gz_file]"
    exit 1
fi

colormsg "Importing filesystem from '$INPUT_FILE'..."
colormsg "Restoring Docker metadata (ENV, ENTRYPOINT)..."

# We use 'docker import' with --change flags to manually restore the Dockerfile instructions
# that were lost during 'docker export'.
# 1. Restore PATH (combining system path + uv path + dynawo path)
# 2. Restore DEBIAN_FRONTEND
# 3. Restore ENTRYPOINT script
cat "$INPUT_FILE" | docker import \
    --change "ENV PATH=/opt/dynawo_install/dynawo:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    --change "ENV DEBIAN_FRONTEND=noninteractive" \
    --change "ENTRYPOINT [\"/start_dycov.sh\"]" \
    - "$TARGET_IMAGE"

if [ $? -eq 0 ]; then
    colormsg "Success! Image '$TARGET_IMAGE' created."
    colormsg "You can now run the tool using './run_dycov_docker.sh .'"
else
    errormsg "Import failed."
    exit 1
fi