#!/bin/bash
#
# build.sh: A simple script to build the Docker image (GFM-only version).
# It is intended to be run in the GFM-only directory.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

# Ask for the container TAG only
if [[ $# -ne 1 ]]; then
    echo
    echo -e "$0: A tag is required.\n"
    echo -e "Usage: $0 <TAG>\n"
    echo
    exit 4
fi
TAG=$1

# Ensure we are in the correct directory
if [ ! -f "Dockerfile" ]; then
    echo "ERROR: Please run this script from the 'GFM-only' directory where Dockerfile is located."
    exit 1
fi

ROOT_DIR=".."

# Build the python package
if [ ! -d ../dist ]; then
  echo "Building package with uv..."
  (cd "$ROOT_DIR" && uv build --out-dir dist)
  
  PKG=$(find "$ROOT_DIR/dist" -iname '*.whl' -printf "%Ts %P\n" | sort -n | tail -n 1 | cut -d' ' -f2)
  rm -f "$PKG"
  cp "$ROOT_DIR/dist/$PKG" .
else 
  # If dist exists, we still rebuild to ensure we have the latest changes
  echo "Re-building package with uv..."
  (cd "$ROOT_DIR" && uv build --out-dir dist)
  PKG=$(find "$ROOT_DIR/dist" -iname '*.whl' -printf "%Ts %P\n" | sort -n | tail -n 1 | cut -d' ' -f2)
  rm -f "$PKG"
  cp "$ROOT_DIR/dist/$PKG" .
fi

# Copy the examples folder from the repo root to the current directory
# so Docker can see it (Docker build context restriction).
EXAMPLES_DIR="examples"
rm -rf "$EXAMPLES_DIR" # Clean up any previous copy
echo "Copying examples directory..."
cp -a "$ROOT_DIR/examples" "$EXAMPLES_DIR"

# Launch the build (GFM-only version)
rm -f build.log
echo "Starting Docker build (GFM-only)..."
docker build -t dycov-GFM-only:latest -t dycov-GFM-only:"$TAG" \
             --build-arg dycov_PKG="$PKG" \
             --build-arg dycov_EXAMPLES="$EXAMPLES_DIR" \
             .

# Clean up artifacts to keep the folder clean
rm -f "$PKG"
rm -rf "$EXAMPLES_DIR"

echo "Build complete. Image tagged as dycov-GFM-only:$TAG and dycov-GFM-only:latest"