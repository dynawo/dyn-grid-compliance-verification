#!/bin/bash
#
# import_image.sh: Load the Dycov Docker image from a compressed file.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

INPUT_FILE="dycov_image.tar.gz"

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

# Check if file provided as argument, otherwise use default
if [ $# -ge 1 ]; then
    INPUT_FILE="$1"
fi

if [ ! -f "$INPUT_FILE" ]; then
    errormsg "ERROR: File '$INPUT_FILE' not found."
    errormsg "Usage: $0 [path_to_tar_gz_file]"
    exit 1
fi

colormsg "Importing Docker image from '$INPUT_FILE'..."
colormsg "This process may take a minute..."

if docker load < "$INPUT_FILE"; then
    colormsg "Success!"
    colormsg "The image 'dycov:latest' is now available in Docker."
    echo ""
    echo "You can now run the tool using './run_dycov_docker.sh <WORK_DIRECTORY>'"
else
    errormsg "Failed to load image."
    exit 1
fi