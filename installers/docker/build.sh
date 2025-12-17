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

# CHANGE: Now we go up two levels to find the project root
# (From installers/docker -> installers -> ProjectRoot)
ROOT_DIR="../.."

# Validate execution directory
if [ ! -f "Dockerfile" ]; then
    echo "ERROR: Please run this script from the 'installers/docker' directory (where Dockerfile is located)."
    exit 1
fi

# Validate Root Directory sanity check
# We check if pyproject.toml exists two levels up to confirm we are in the right structure
if [ ! -f "$ROOT_DIR/pyproject.toml" ]; then
    echo "ERROR: Could not find 'pyproject.toml' at '$ROOT_DIR'."
    echo "       Are you sure you are running this from 'installers/docker'?"
    exit 1
fi

# 1. Build Python Package (uv)
# We run the build from the ROOT_DIR
if [ ! -d "$ROOT_DIR/dist" ]; then
  echo "Building package with uv..."
  (cd "$ROOT_DIR" && uv build --out-dir dist)
else 
  echo "Re-building package with uv (ensure latest changes)..."
  (cd "$ROOT_DIR" && uv build --out-dir dist)
fi

# Find the latest wheel in the project dist folder
PKG=$(find "$ROOT_DIR/dist" -iname '*.whl' -printf "%Ts %P\n" | sort -n | tail -n 1 | cut -d' ' -f2)

if [ -z "$PKG" ]; then
    echo "ERROR: No .whl package found in $ROOT_DIR/dist after build."
    exit 1
fi

rm -f "$PKG"
echo "Copying package $PKG..."
cp "$ROOT_DIR/dist/$PKG" .

# 2. Prepare Context (Examples)
EXAMPLES_DIR="examples"
rm -rf "$EXAMPLES_DIR"
echo "Copying examples directory..."
if [ -d "$ROOT_DIR/examples" ]; then
    cp -a "$ROOT_DIR/examples" "$EXAMPLES_DIR"
else
    echo "WARNING: Examples directory not found at $ROOT_DIR/examples"
    mkdir "$EXAMPLES_DIR" # Create empty to avoid Docker build error
fi

# 3. Prepare Context (Dynawo)
DYNAWO_DIR_NAME=dynawo_build
if [ ! -d "$DYNAWO_HOST_PATH" ]; then
   echo "ERROR: Dynawo path $DYNAWO_HOST_PATH not found."
   rm -f "$PKG"; rm -rf "$EXAMPLES_DIR"
   exit 1
fi

rm -rf "$DYNAWO_DIR_NAME"
echo "Copying Dynawo from host ($DYNAWO_HOST_PATH)... This may take a moment."
cp -a "$DYNAWO_HOST_PATH" "$DYNAWO_DIR_NAME"

# Check if the expected executable exists (sanity check)
if [ ! -f "$DYNAWO_DIR_NAME/dynawo/dynawo.sh" ]; then
    echo "ERROR: Expected executable not found at '$DYNAWO_HOST_PATH/dynawo/dynawo.sh'"
    rm -rf "$DYNAWO_DIR_NAME"; rm -f "$PKG"; rm -rf "$EXAMPLES_DIR"
    exit 1
fi

# 4. Launch the build
rm -f build.log
echo "Starting Docker build..."
docker build -t dycov:latest -t dycov:"$TAG" \
             --build-arg dycov_PKG="$PKG" \
             --build-arg dycov_EXAMPLES="$EXAMPLES_DIR" \
             --build-arg DYNAWO_DIR_NAME="$DYNAWO_DIR_NAME" \
             .

# 5. Clean up artifacts
rm -f "$PKG"
rm -rf "$EXAMPLES_DIR"
rm -rf "$DYNAWO_DIR_NAME"

echo "Build complete. Image tagged as dycov:$TAG and dycov:latest"