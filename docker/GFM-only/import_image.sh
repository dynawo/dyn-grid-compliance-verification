#!/bin/bash
#
# import_image.sh: Load the Dycov GFM-only Docker image.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

INPUT_FILE="dycov_image_GFM-only.tar.gz"
DOWNLOAD_URL=""

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

# --- Argument parsing ---
while [[ $# -gt 0 ]]; do
  case $1 in
    -u|--url)
      if [ -n "$2" ]; then
        DOWNLOAD_URL="$2"
        shift # past argument
        shift # past value
      else
        errormsg "ERROR: Argument for --url is missing."
        exit 1
      fi
      ;;
    -h|--help)
      echo "Usage: $0 [options] [file_path]"
      echo ""
      echo "Options:"
      echo "  -u, --url <link>   Download the image distribution from a URL before loading."
      echo "  -h, --help         Show this help message."
      echo ""
      echo "Arguments:"
      echo "  file_path          Path to the local .tar.gz file (default: $INPUT_FILE)"
      exit 0
      ;;
    *)
      INPUT_FILE="$1" # Save backward compatibility for positional argument
      shift # past argument
      ;;
  esac
done

# --- Download logic ---
if [ -n "$DOWNLOAD_URL" ]; then
    colormsg "URL provided. Downloading image distribution..."
    colormsg "Source: $DOWNLOAD_URL"
    colormsg "Destination: $INPUT_FILE"
    
    if command -v curl &> /dev/null; then
        curl -L -o "$INPUT_FILE" "$DOWNLOAD_URL"
    elif command -v wget &> /dev/null; then
        wget -O "$INPUT_FILE" "$DOWNLOAD_URL"
    else
        errormsg "ERROR: Neither 'curl' nor 'wget' found. Cannot download file."
        exit 1
    fi
    
    if [ $? -eq 0 ]; then
        colormsg "Download completed successfully."
    else
        errormsg "ERROR: Download failed."
        exit 1
    fi
fi

# --- File validation ---
if [ ! -f "$INPUT_FILE" ]; then
    errormsg "ERROR: File '$INPUT_FILE' not found."
    errormsg "Usage: $0 [path_to_tar_gz_file] OR $0 --url <link>"
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