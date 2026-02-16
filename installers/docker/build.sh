#!/bin/bash
#
# build.sh: Builds the Docker image from source.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#

set -o nounset -o noclobber
set -o errexit -o pipefail 

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <TAG> <DYNAWO_HOST_PATH>"
    exit 4
fi

TAG=$1
DYNAWO_HOST_PATH=$2
ROOT_DIR="../.."

# Temporary Artifacts to clean up
EXAMPLES_DIR="examples"
DYNAWO_DIR_NAME="dynawo_build"
PKG=""

# This ensures that even if the script crashes (Ctrl+C or error),
# we remove the temporary copies of Dynawo and Examples.
cleanup() {
    echo "Cleaning up..."
    rm -rf "$EXAMPLES_DIR"
    rm -rf "$DYNAWO_DIR_NAME"
    [ -n "$PKG" ] && rm -f "$PKG"
}
trap cleanup EXIT

# Validate execution directory
if [ ! -f "Dockerfile" ]; then
    echo "ERROR: Please run this from 'installers/docker'."
    exit 1
fi

if [ ! -f "$ROOT_DIR/pyproject.toml" ]; then
    echo "ERROR: Could not find 'pyproject.toml' at '$ROOT_DIR'."
    exit 1
fi

# 1. Build Python Package (uv)
echo "Building Python package..."
(cd "$ROOT_DIR" && uv build --out-dir dist)

# Find latest wheel
PKG=$(find "$ROOT_DIR/dist" -iname '*.whl' -printf "%Ts %P\n" | sort -n | tail -n 1 | cut -d' ' -f2)

if [ -z "$PKG" ]; then
    echo "ERROR: No .whl package found."
    exit 1
fi

# Copy wheel to local context
cp "$ROOT_DIR/dist/$PKG" .

# 2. Prepare Context (Examples)
echo "Copying examples..."
if [ -d "$ROOT_DIR/examples" ]; then
    cp -a "$ROOT_DIR/examples" "$EXAMPLES_DIR"
else
    mkdir "$EXAMPLES_DIR"
fi

# 3. Prepare Context (Dynawo)
if [ ! -d "$DYNAWO_HOST_PATH" ]; then
   echo "ERROR: Dynawo path $DYNAWO_HOST_PATH not found."
   exit 1
fi

echo "Copying Dynawo from host ($DYNAWO_HOST_PATH)..."
# Using -L to dereference symlinks ensures the image gets the actual files,
# not dead links from the host system.
cp -rL "$DYNAWO_HOST_PATH" "$DYNAWO_DIR_NAME"

# Sanity check
if [ ! -f "$DYNAWO_DIR_NAME/dynawo/dynawo.sh" ]; then
    echo "ERROR: Expected executable not found at '$DYNAWO_HOST_PATH/dynawo/dynawo.sh'"
    exit 1
fi

# 4. Launch the build
echo "Starting Docker build..."
docker build -t dycov:latest -t dycov:"$TAG" \
             --build-arg dycov_PKG="$PKG" \
             --build-arg dycov_EXAMPLES="$EXAMPLES_DIR" \
             --build-arg DYNAWO_DIR_NAME="$DYNAWO_DIR_NAME" \
             .

echo "Build complete. Image tagged as dycov:$TAG and dycov:latest"
# Cleanup happens automatically via trap