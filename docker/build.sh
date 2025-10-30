#!/bin/bash
#
# build.sh: A simple script to build the Docker image.  It is intended to be run
# here under the docker directory, in a local git clone repo.
#
# (c) 2023/24 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     demiguelm@aia.es
#     omsg@aia.es
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

# The pip package needs to appear at the build directory level
if [ ! -d ../dist ]; then
  cd ..
  echo "Building package with uv..."
  uv build --out-dir dist
  cd docker
  PKG=$(find ../dist -iname '*.whl' -printf "%Ts %P\n" | sort -n | tail -n 1 | cut -d' ' -f2)  # newest wheel
  rm -f "$PKG"
  ln ../dist/"$PKG" .
  rm -rf ../dist
else 
  PKG=$(find ../dist -iname '*.whl' -printf "%Ts %P\n" | sort -n | tail -n 1 | cut -d' ' -f2)  # newest wheel
  rm -f "$PKG"
  ln ../dist/"$PKG" .
fi

# The examples also need to be visible at the build directory level
EXAMPLES=examples
cp -a ../examples .

# Dynawo: Copy the host directory to the build context
DYNAWO_DIR_NAME=dynawo_build
if [ ! -d "$DYNAWO_HOST_PATH" ]; then
   echo "ERROR: Dynawo path $DYNAWO_HOST_PATH not found."
   exit 1
fi
rm -rf "$DYNAWO_DIR_NAME" # Clean up previous
cp -a "$DYNAWO_HOST_PATH" "$DYNAWO_DIR_NAME"

# Check if the expected executable exists
if [ ! -f "$DYNAWO_DIR_NAME/dynawo/dynawo.sh" ]; then
    echo "ERROR: Expected executable not found at '$DYNAWO_HOST_PATH/dynawo/dynawo.sh'"
    rm -rf "$DYNAWO_DIR_NAME" # Clean up
    exit 1
fi

# Launch the build
rm -f build.log
docker build -t dycov:latest -t dycov:"$TAG" \
             --build-arg dycov_PKG="$PKG" \
             --build-arg dycov_EXAMPLES="$EXAMPLES" \
             --build-arg DYNAWO_DIR_NAME="$DYNAWO_DIR_NAME" \
             .

# Clean up
rm -rf "$PKG" "$EXAMPLES" "$DYNAWO_DIR_NAME"