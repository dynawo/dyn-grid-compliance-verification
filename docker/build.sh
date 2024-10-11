#!/bin/bash
#
# build.sh: A simple script to build the Docker image.  It is intended to be run
# here under the docker directoxpry, in a local git clone repo where the pip
# package has already been built.
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


# Ask for the container TAG
if [[ $# -ne 1 ]]; then
    echo
    echo -e "$0: A tag is required for the image to be built.\n"
    echo
    exit 4
fi
TAG=$1

# The pip package needs to appear at the build directory level
if [ ! -d ../dist ]; then
  cd ..
  pip install build
  echo "Building package..."
  python3 -m build
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

# Dynawo: instead of downloading, unpacking, and using COPY, we'll do it all in
# the Dockerfile at build time.  (Note: if the Dynawo ZIP was published as a
# tar.gz, we could download it here and use ADD instead.)
ZIP="Dynawo_omc_V1.6.0.zip"

# Launch the build
rm -f build.log
docker build -t dgcv:latest -t dgcv:"$TAG" \
             --build-arg DGCV_PKG="$PKG" \
             --build-arg DGCV_EXAMPLES="$EXAMPLES" \
             --build-arg DWO_ZIP="$ZIP" \
             .

# Clean up
rm -rf "$PKG" "$EXAMPLES"

