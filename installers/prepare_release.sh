#!/bin/bash
#
# prepare_release.sh
#
# Prepares all artifacts needed for a Dycov GitHub release.
# Must be run from the root of the repository.
#
# Usage:
#   ./prepare_release.sh VERSION DYNAWO_DIR
#
# Example:
#   ./prepare_release.sh v0.9.3 /path/to/dynawo
#
# Output directory: ./release_VERSION (created automatically)
#
# Artifacts generated:
#   - Dynawo_omc_v1.8.0.zip        (zipped from DYNAWO_DIR)
#   - linux_install.sh              (updated with new version and URLs)
#   - dycov_rawimage.tar.gz         (Docker image export)
#   - import_image.sh
#   - run_dycov_docker.sh
#
# (c) Rte - Grupo AIA
#

set -o nounset -o errexit -o pipefail

###############################################################################
# Config
###############################################################################

# Fixed Dynawo zip name — update here when Dynawo version changes
DYNAWO_ZIP_NAME="Dynawo_omc_v1.8.0.zip"

RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()  { echo -e "\n${GREEN}==> $*${NC}"; }

###############################################################################
# Arguments
###############################################################################
if [[ $# -ne 2 ]]; then
    echo "Usage: $0 VERSION DYNAWO_DIR"
    echo "  VERSION     e.g. v0.9.3"
    echo "  DYNAWO_DIR  path to the Dynawo installation directory"
    exit 1
fi

VERSION="$1"
DYNAWO_DIR="$2"

# Validate version format
[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] \
    || error "VERSION must follow the format vX.Y.Z (e.g. v0.9.3), got: '$VERSION'"

# Validate Dynawo directory
[[ -d "$DYNAWO_DIR" ]] || error "Dynawo directory not found: $DYNAWO_DIR"
DYNAWO_DIR=$(realpath "$DYNAWO_DIR")

# Version without 'v' for pyproject.toml
VERSION_PLAIN="${VERSION#v}"

# Repo root = current directory
REPO_ROOT="$PWD"

###############################################################################
# Validate expected repo files
###############################################################################
LINUX_INSTALL="$REPO_ROOT/installers/linux_install.sh"
PYPROJECT="$REPO_ROOT/pyproject.toml"
BUILD_SH="$REPO_ROOT/installers/docker/build.sh"
EXPORT_SH="$REPO_ROOT/installers/docker/export_image.sh"
IMPORT_SH="$REPO_ROOT/installers/docker/import_image.sh"
RUN_SH="$REPO_ROOT/installers/docker/run_dycov_docker.sh"

for f in "$LINUX_INSTALL" "$PYPROJECT" "$BUILD_SH" "$EXPORT_SH" "$IMPORT_SH" "$RUN_SH"; do
    [[ -f "$f" ]] || error "Expected file not found: $f"
done

# Output directory
OUTPUT_DIR="$REPO_ROOT/release_${VERSION}"
mkdir -p "$OUTPUT_DIR"

info "Version:         $VERSION"
info "Dynawo dir:      $DYNAWO_DIR"
info "Output dir:      $OUTPUT_DIR"

###############################################################################
# Step 1 — Generate Dynawo ZIP
###############################################################################
step "Step 1: Generating $DYNAWO_ZIP_NAME from $DYNAWO_DIR..."

DYNAWO_ZIP="$OUTPUT_DIR/$DYNAWO_ZIP_NAME"
DYNAWO_PARENT=$(dirname "$DYNAWO_DIR")
DYNAWO_BASENAME=$(basename "$DYNAWO_DIR")

cd "$DYNAWO_PARENT"
zip -qr "$DYNAWO_ZIP" "$DYNAWO_BASENAME"
info "$DYNAWO_ZIP_NAME generated."

###############################################################################
# Step 2 — Update pyproject.toml in the repo
###############################################################################
step "Step 2: Updating pyproject.toml (version -> $VERSION_PLAIN)..."

sed -i -E "s|^version = \"[^\"]+\"|version = \"${VERSION_PLAIN}\"|" "$PYPROJECT"

info "pyproject.toml updated: $(grep '^version = ' "$PYPROJECT" | head -1)"

###############################################################################
# Step 3 — Generate updated linux_install.sh in output dir
###############################################################################
step "Step 3: Generating updated linux_install.sh..."

DYNAWO_SHA256=$(sha256sum "$DYNAWO_ZIP" | cut -d' ' -f1)
info "SHA256: $DYNAWO_SHA256"

LINUX_INSTALL_OUT="$OUTPUT_DIR/linux_install.sh"
cp "$LINUX_INSTALL" "$LINUX_INSTALL_OUT"

# Update TARGET_BRANCH (with 'v' prefix, matches the git tag)
sed -i -E "s|^TARGET_BRANCH=.*|TARGET_BRANCH=\"${VERSION}\"|" "$LINUX_INSTALL_OUT"

# Update DYNAWO_SHA256SUM with the checksum of the zip generated in Step 1
sed -i -E "s|^DYNAWO_SHA256SUM=.*|DYNAWO_SHA256SUM=\"${DYNAWO_SHA256}\"|" "$LINUX_INSTALL_OUT"

info "linux_install.sh updated."
info "--- Relevant lines ---"
grep -E "^(TARGET_BRANCH|DYNAWO_SHA256SUM)=" "$LINUX_INSTALL_OUT"
echo "----------------------"

###############################################################################
# Step 4 — Build Docker image
###############################################################################
step "Step 4: Building Docker image..."

cd "$REPO_ROOT/installers/docker"
bash build.sh "$VERSION" "$DYNAWO_DIR"
info "Docker image built."

###############################################################################
# Step 5 — Export Docker image
###############################################################################
step "Step 5: Exporting Docker image..."

cd "$REPO_ROOT/installers/docker"
bash export_image.sh
info "Docker image exported."

# Locate generated tarball (export_image.sh should leave it in current dir)
RAW_IMAGE=$(find "$REPO_ROOT/installers/docker" -maxdepth 1 -name "dycov_rawimage.tar.gz" | head -1)
[[ -z "$RAW_IMAGE" ]] && error "dycov_rawimage.tar.gz not found after export. Check export_image.sh output."

###############################################################################
# Step 6 — Collect all artifacts in output dir
###############################################################################
step "Step 6: Collecting release artifacts..."

mv "$RAW_IMAGE"  "$OUTPUT_DIR/dycov_rawimage.tar.gz"
cp "$IMPORT_SH"  "$OUTPUT_DIR/import_image.sh"
cp "$RUN_SH"     "$OUTPUT_DIR/run_dycov_docker.sh"

info "All artifacts ready."

###############################################################################
# Summary
###############################################################################
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Release ${VERSION} artifacts ready in: ${OUTPUT_DIR}${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Files to upload to GitHub release:"
ls -lh "$OUTPUT_DIR" | grep -v '^total' | awk '{print "  " $NF " (" $5 ")"}'
echo ""
warn "pyproject.toml has been updated in the repo. Remember to commit and push before creating the GitHub release."
echo ""
