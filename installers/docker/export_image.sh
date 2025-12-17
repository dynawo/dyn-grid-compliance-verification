#!/bin/bash
#
# export_image.sh: Exports the 'dycov:latest' container filesystem to a .tar.gz file.
#
# STRATEGY:
# We use 'docker export' (filesystem export) instead of 'docker save'.
# This creates a flat tarball suitable for 'wsl --import' (Windows Standalone).
# However, this strips Docker metadata (ENV, ENTRYPOINT), which 'import_image.sh'
# must restore for Docker users.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

set -o nounset -o noclobber
set -o errexit -o pipefail 

IMAGE_NAME="dycov:latest"
TEMP_CONTAINER_NAME="dycov_export_temp"
OUTPUT_FILE="dycov_dist.tar.gz"

GREEN="\033[1;32m"
RED="\033[1;31m"
NC="\033[0m"

colormsg() {
    echo -e "${GREEN}$1${NC}"
}

errormsg() {
    echo -e "${RED}$1${NC}" >&2
}

# Check if the build exists
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    errormsg "ERROR: Docker image '$IMAGE_NAME' not found."
    errormsg "Please run './build.sh <TAG> <DYNAWO_PATH>' first."
    exit 1
fi

colormsg "Preparing to export '$IMAGE_NAME'..."

# 1. Create a temporary container (without running it) to allow exporting the filesystem
# Force remove any leftover temp container
docker rm -f "$TEMP_CONTAINER_NAME" >/dev/null 2>&1 || true
docker create --name "$TEMP_CONTAINER_NAME" "$IMAGE_NAME" > /dev/null

colormsg "Exporting filesystem to '$OUTPUT_FILE'..."
colormsg "Note: This creates a flat filesystem for WSL compatibility."

# 2. Export (tar) and compress (gzip)
# We pipe directly to gzip to create a .tar.gz
if docker export "$TEMP_CONTAINER_NAME" | gzip > "$OUTPUT_FILE"; then
    colormsg "Success!"
    colormsg "Artifact created: $PWD/$OUTPUT_FILE"
    echo ""
    echo "Distribution Guide:"
    echo " - For WSL Standalone: Use 'wsl --import <Name> <Path> $OUTPUT_FILE'"
    echo " - For Docker (Linux/Win): Use './import_image.sh $OUTPUT_FILE'"
else
    errormsg "Failed to export image."
    docker rm -f "$TEMP_CONTAINER_NAME" >/dev/null
    rm -f "$OUTPUT_FILE"
    exit 1
fi

# 3. Cleanup
docker rm -f "$TEMP_CONTAINER_NAME" >/dev/null