#!/bin/bash
#
# build.sh: A simple script to build the Docker image. It is intended to be run
# here under the docker directory, in a local git clone repo.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail 

# Ask for the container TAG and Dynawo path
if [[ $# -ne 2 ]]; then
    echo
    echo -e "$0: A tag and the path to the Dynawo installation are required.\n"
    echo -e "Usage: $0 <TAG> <DYNAWO_HOST_PATH>\n"
    echo
    exit 4
fi
TAG=$1
DYNAWO_HOST_PATH=$2

# Ensure we are in the docker directory
if [ ! -f "Dockerfile" ]; then
    echo "ERROR: Please run this script from the 'docker' directory."
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
  # We leave the dist folder there as cache
else 
  # If dist exists, we still rebuild to ensure we have the latest changes
  echo "Re-building package with uv..."
  (cd "$ROOT_DIR" && uv build --out-dir dist)
  PKG=$(find "$ROOT_DIR/dist" -iname '*.whl' -printf "%Ts %P\n" | sort -n | tail -n 1 | cut -d' ' -f2)
  rm -f "$PKG"
  cp "$ROOT_DIR/dist/$PKG" .
fi

# The examples also need to be visible at the build directory level
EXAMPLES=examples
rm -rf "$EXAMPLES" # Clean previous
cp -a "$ROOT_DIR/examples" .

# Dynawo: Copy the host directory to the build context
DYNAWO_DIR_NAME=dynawo_build
if [ ! -d "$DYNAWO_HOST_PATH" ]; then
   echo "ERROR: Dynawo path $DYNAWO_HOST_PATH not found."
   rm -f "$PKG"
   rm -rf "$EXAMPLES"
   exit 1
fi
rm -rf "$DYNAWO_DIR_NAME" # Clean up previous
echo "Copying Dynawo from host ($DYNAWO_HOST_PATH)... This may take a moment."
cp -a "$DYNAWO_HOST_PATH" "$DYNAWO_DIR_NAME"

# Check if the expected executable exists
if [ ! -f "$DYNAWO_DIR_NAME/dynawo/dynawo.sh" ]; then
    echo "ERROR: Expected executable not found at '$DYNAWO_HOST_PATH/dynawo/dynawo.sh'"
    rm -rf "$DYNAWO_DIR_NAME"
    rm -f "$PKG"
    rm -rf "$EXAMPLES"
    exit 1
fi

# Launch the build
rm -f build.log
echo "Starting Docker build..."
docker build -t dycov:latest -t dycov:"$TAG" \
             --build-arg dycov_PKG="$PKG" \
             --build-arg dycov_EXAMPLES="$EXAMPLES" \
             --build-arg DYNAWO_DIR_NAME="$DYNAWO_DIR_NAME" \
             .

# Clean up artifacts to keep the docker folder clean
rm -f "$PKG"
rm -rf "$EXAMPLES"
rm -rf "$DYNAWO_DIR_NAME"

echo "Build complete. Image tagged as dycov:$TAG and dycov:latest"