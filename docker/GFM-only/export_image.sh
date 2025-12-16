#!/bin/bash
#
# export_image.sh: Export the built 'dycov-GFM-only:latest' Docker image.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

IMAGE_NAME="dycov-GFM-only:latest"
OUTPUT_FILE="dycov_image_GFM-only.tar.gz"

# Colors for output
GREEN="\033[1;32m"
RED="\033[1;31m"
NC="\033[0m"

colormsg() {
    echo -e "${GREEN}$1${NC}"
}

errormsg() {
    echo -e "${RED}$1${NC}" >&2
}

# Check if the image exists locally
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    errormsg "ERROR: Docker image '$IMAGE_NAME' not found."
    errormsg "Please run './build.sh <TAG>' first."
    exit 1
fi

colormsg "Exporting Docker image '$IMAGE_NAME'..."

# Save and compress using gzip
if docker save "$IMAGE_NAME" | gzip > "$OUTPUT_FILE"; then
    colormsg "Success!"
    colormsg "Image exported to: $PWD/$OUTPUT_FILE"
    echo ""
    echo "You can now transfer '$OUTPUT_FILE' and 'import_image.sh' to another machine."
else
    errormsg "Failed to export image."
    rm -f "$OUTPUT_FILE" # Clean up partial file
    exit 1
fi