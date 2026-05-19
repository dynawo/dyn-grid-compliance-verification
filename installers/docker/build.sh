#!/bin/bash
#
# build.sh: Builds the Dycov Docker image.
#

set -o nounset -o noclobber -o errexit -o pipefail

########################################
# Argument parsing
########################################

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <TAG> <DYNAWO_HOST_PATH>"
    exit 4
fi

TAG="$1"
DYNAWO_HOST_PATH="$2"
ROOT_DIR="../.."

########################################
# Preconditions
########################################

if [[ ! -f "Dockerfile" ]]; then
    echo "ERROR: Dockerfile not found. Run from installers/docker/"
    exit 1
fi

if [[ ! -f "start_dycov.sh" ]]; then
    echo "ERROR: start_dycov.sh not found in installers/docker/"
    exit 1
fi

if [[ ! -f "$ROOT_DIR/pyproject.toml" ]]; then
    echo "ERROR: pyproject.toml not found at $ROOT_DIR"
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: 'uv' is not installed or not in PATH."
    exit 1
fi

########################################
# Create unified temporary build context
########################################

TEMP_DIR=$(mktemp -d temp.XXXXXX)

EXAMPLES_DIR="$TEMP_DIR/examples"
DYNAWO_DIR_NAME="$TEMP_DIR/dynawo_build"

mkdir -p "$EXAMPLES_DIR" "$DYNAWO_DIR_NAME"

cleanup() {
    echo "Cleaning up temp directory..."
    rm -rf "$TEMP_DIR" || true
}
trap cleanup EXIT


########################################
# 1. Clean old artifacts + build package
########################################

echo "Cleaning old build artifacts..."
rm -rf "$ROOT_DIR/dist"
mkdir "$ROOT_DIR/dist"

echo "Building Python package..."
(
    cd "$ROOT_DIR"
    uv build --out-dir dist
)

########################################
# 2. Locate exactly one wheel (portable: macOS/Linux)
########################################

NWHEELS=$(find "$ROOT_DIR/dist" -type f  -iname "*.whl" | wc -l)
 
# There should be only one wheel file
if [[ $NWHEELS -eq 0 ]]; then
    echo "ERROR: No wheel files found in dist/"
    exit 1
elif [[ $NWHEELS -ne 1 ]]; then
    echo "ERROR: Multiple wheel files found in dist/ (expected one, found: $NWHEELS)"
    exit 1
fi
PKG=$(find "$ROOT_DIR/dist" -type f  -iname "*.whl")
PKG_BASENAME=$(basename "$PKG")
echo "Found unique wheel: $PKG_BASENAME"


########################################
## 3. Version Consistency Check (tag vs wheel)
########################################

# Extract version from wheel filename
WHEEL_VERSION=$(echo "$PKG_BASENAME" | sed -E 's/^[^-]+-([0-9]+\.[0-9]+\.[0-9]+)-.*$/\1/')

if [[ -z "$WHEEL_VERSION" ]]; then
    echo "ERROR: Could not extract version from wheel filename"
    exit 1
fi

# Extract numeric part of tag ("v1.0.0" -> "1.0.0")
TAG_VERSION="${TAG#v}"

if [[ "$WHEEL_VERSION" != "$TAG_VERSION" ]]; then
    echo "ERROR: Wheel version mismatch vs tag!"
    echo "  tag version:   $TAG_VERSION"
    echo "  wheel version: $WHEEL_VERSION"
    exit 1
fi

echo "Version check OK:"
echo " - wheel version = $WHEEL_VERSION"
echo " - tag           = $TAG"


########################################
# 4. Copy wheel into TEMP_DIR
########################################

cp "$PKG" "$TEMP_DIR/"


########################################
# 5. Copy examples
########################################

echo "Copying examples..."
if [[ -d "$ROOT_DIR/examples" ]]; then
    cp -a "$ROOT_DIR/examples/"* "$EXAMPLES_DIR/" 2>/dev/null || true
fi


########################################
# 6. Copy Dynawo
########################################

if [[ ! -d "$DYNAWO_HOST_PATH" ]]; then
    echo "ERROR: Dynawo path '$DYNAWO_HOST_PATH' does not exist."
    exit 1
fi

echo "Copying Dynawo from host ($DYNAWO_HOST_PATH)..."

mkdir -p "$DYNAWO_DIR_NAME/dynawo"
cp -R "$DYNAWO_HOST_PATH/"* "$DYNAWO_DIR_NAME/dynawo/"

if [[ ! -f "$DYNAWO_DIR_NAME/dynawo/dynawo.sh" ]]; then
    echo "ERROR: Expected dynawo.sh missing in dynawo_build/dynawo/"
    exit 1
fi


########################################
# 7. Copy Dockerfile + start script
########################################

cp Dockerfile "$TEMP_DIR/"
cp start_dycov.sh "$TEMP_DIR/"


########################################
# 8. Docker build (context = TEMP_DIR)
########################################

echo "Starting Docker build using context $TEMP_DIR..."

docker build \
    -t "dycov:latest" \
    -t "dycov:$TAG" \
    --build-arg dycov_PKG="$PKG_BASENAME" \
    --build-arg dycov_EXAMPLES="examples" \
    --build-arg DYNAWO_DIR_NAME="dynawo_build" \
    "$TEMP_DIR"

echo "Build complete:"
echo "  dycov:latest"
echo "  dycov:$TAG"
# Cleanup happens automatically via trap