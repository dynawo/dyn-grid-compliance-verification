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

INPUT_ARG="dycov_dist.tar.gz"
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

# Allow passing a different file OR a URL as argument
if [ "$#" -ge 1 ]; then
    INPUT_ARG="$1"
fi

# Function to run the docker import command
# We use 'docker import' with --change flags to manually restore the Dockerfile instructions
# that were lost during 'docker export'.
do_import() {
    docker import \
        --change "ENV PATH=/opt/dynawo_install/dynawo:/root/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
        --change "ENV DEBIAN_FRONTEND=noninteractive" \
        --change "ENTRYPOINT [\"/start_dycov.sh\"]" \
        - "$TARGET_IMAGE"
}

# Check if input is a URL (http or https)
if [[ "$INPUT_ARG" =~ ^https?:// ]]; then
    colormsg "Detected URL source: $INPUT_ARG"
    
    if ! command -v curl >/dev/null 2>&1; then
        errormsg "ERROR: 'curl' is required to download from a URL but it is not installed."
        exit 1
    fi

    colormsg "Downloading and importing stream directly (no temp file)..."
    colormsg "Restoring Docker metadata (ENV, ENTRYPOINT)..."
    
    # Pipe curl directly to docker import
    # -L follows redirects, -f fails on HTTP errors, -s shows progress bar implied or silence
    curl -L --fail --progress-bar "$INPUT_ARG" | do_import

# Check if input is a local file
elif [ -f "$INPUT_ARG" ]; then
    colormsg "Importing filesystem from local file '$INPUT_ARG'..."
    colormsg "Restoring Docker metadata (ENV, ENTRYPOINT)..."
    
    cat "$INPUT_ARG" | do_import

else
    errormsg "ERROR: Source '$INPUT_ARG' not found locally and is not a valid URL."
    errormsg "Usage: $0 [path_to_tar_gz_file | http://url/to/file.tar.gz]"
    exit 1
fi

if [ $? -eq 0 ]; then
    colormsg "Success! Image '$TARGET_IMAGE' created."
    colormsg "You can now run the tool using './run_dycov_docker.sh .'"
else
    errormsg "Import failed."
    exit 1
fi