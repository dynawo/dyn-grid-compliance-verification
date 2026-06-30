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
#   - dycov_par_tool.zip            (standalone Dynawo PAR utility)
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
if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: $0 VERSION DYNAWO_DIR [--dry-run]"
    echo "  VERSION     e.g. v0.9.3"
    echo "  DYNAWO_DIR  path to the Dynawo installation directory"
    echo "  --dry-run   skip Git checks"
    exit 1
fi

VERSION="$1"
DYNAWO_DIR="$2"
DRY_RUN=false
if [[ "${3:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

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
# Strict Git safety checks
###############################################################################

step "Checking Git state for release $VERSION"

if [[ "$DRY_RUN" == true ]]; then
    warn "Skipping Git checks (dry-run)"
else
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
      || error "Not inside a Git repository."

    git rev-parse "$VERSION" >/dev/null 2>&1 \
      || error "Tag '$VERSION' does not exist."

    CURRENT_TAG=$(git describe --tags --exact-match 2>/dev/null || true)
    if [[ "$CURRENT_TAG" != "$VERSION" ]]; then
        error "HEAD is not exactly on tag $VERSION (current: ${CURRENT_TAG:-})"
    fi

    if [[ -n "$(git status --porcelain)" ]]; then
        error "Working tree is not clean. Commit or stash changes before releasing."
    fi

    info "Git state OK:"
    info " - Tag: $CURRENT_TAG"
    info " - Commit: $(git rev-parse --short HEAD)"
fi

###############################################################################
# Validate expected repo files
###############################################################################
LINUX_INSTALL="$REPO_ROOT/installers/linux_install.sh"
PYPROJECT="$REPO_ROOT/pyproject.toml"
BUILD_SH="$REPO_ROOT/installers/docker/build.sh"
EXPORT_SH="$REPO_ROOT/installers/docker/export_image.sh"
IMPORT_SH="$REPO_ROOT/installers/docker/import_image.sh"
RUN_SH="$REPO_ROOT/installers/docker/run_dycov_docker.sh"
IMPORT_WSL_BAT="$REPO_ROOT/installers/wsl/import_wsl.bat"
IMPORT_WSL_PS1="$REPO_ROOT/installers/wsl/import_wsl.ps1"
RUN_WSL_PS1="$REPO_ROOT/installers/wsl/run_dycov_wsl.ps1"
TOOLS_DIR="$REPO_ROOT/tools/dynawo_par"

for f in "$LINUX_INSTALL" "$PYPROJECT" "$BUILD_SH" "$EXPORT_SH" "$IMPORT_SH" "$RUN_SH" \
          "$IMPORT_WSL_BAT" "$IMPORT_WSL_PS1" "$RUN_WSL_PS1"; do
    [[ -f "$f" ]] || error "Expected file not found: $f"
done

[[ -d "$TOOLS_DIR" ]] || error "Expected tool directory not found: $TOOLS_DIR"

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
# Step 4 — Build the documentation manuals
###############################################################################
step "Step 4: Building documentation manuals..."

MANUAL_BUILD_DIR="$REPO_ROOT/docs/manual/build"

# Clean any previous build
rm -rf "$MANUAL_BUILD_DIR"

# Install sphinx in a temporary venv and build
uv venv "$REPO_ROOT/.manual_venv" --python 3.13 --quiet
source "$REPO_ROOT/.manual_venv/bin/activate"
uv pip install -q sphinx
cd "$REPO_ROOT/docs/manual"
make latexpdf > /dev/null 2>&1
make html > /dev/null 2>&1
deactivate
rm -rf "$REPO_ROOT/.manual_venv"

info "Manuals built:"
info " - HTML: $MANUAL_BUILD_DIR/html"
info " - PDF:  $MANUAL_BUILD_DIR/latex/dycov.pdf"

###############################################################################
# Step 5 — Build Docker image
###############################################################################
step "Step 5: Building Docker image..."

cd "$REPO_ROOT/installers/docker"
bash build.sh "$VERSION" "$DYNAWO_DIR" ${DRY_RUN:+--dry-run}
info "Docker image built."

###############################################################################
# Step 6 — Export Docker image
###############################################################################
step "Step 6: Exporting Docker image..."

cd "$REPO_ROOT/installers/docker"
bash export_image.sh
info "Docker image exported."

# Locate generated tarball (export_image.sh should leave it in current dir)
RAW_IMAGE=$(find "$REPO_ROOT/installers/docker" -maxdepth 1 -name "dycov_rawimage.tar.gz" | head -1)
[[ -z "$RAW_IMAGE" ]] && error "dycov_rawimage.tar.gz not found after export. Check export_image.sh output."

###############################################################################
# Step 7 — Collect all artifacts in output dir
###############################################################################
step "Step 7: Collecting release artifacts..."

mv "$RAW_IMAGE"       "$OUTPUT_DIR/dycov_rawimage.tar.gz"
cp "$IMPORT_SH"       "$OUTPUT_DIR/import_image.sh"
cp "$RUN_SH"          "$OUTPUT_DIR/run_dycov_docker.sh"
cp "$IMPORT_WSL_BAT"  "$OUTPUT_DIR/import_wsl.bat"
cp "$IMPORT_WSL_PS1"  "$OUTPUT_DIR/import_wsl.ps1"
cp "$RUN_WSL_PS1"     "$OUTPUT_DIR/run_dycov_wsl.ps1"

# Standalone Dynawo PAR utility, as a directly-downloadable release artifact.
# Built from a cleaned staging copy using the SAME steps as the Docker context
# (installers/docker/build.sh), so the zip and the image ship identical content.
rm -f "$OUTPUT_DIR/dycov_par_tool.zip"
TOOL_STAGE=$(mktemp -d)
cp -a "$TOOLS_DIR" "$TOOL_STAGE/"
find "$TOOL_STAGE" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
( cd "$TOOL_STAGE" && zip -qr "$OUTPUT_DIR/dycov_par_tool.zip" dynawo_par )
rm -rf "$TOOL_STAGE"
info "Bundled standalone tool: dycov_par_tool.zip"

info "All artifacts ready."

###############################################################################
# Step 8 — Remove Docker images
###############################################################################
step "Step 8: Removing Docker images..."

for tag in "dycov:latest" "dycov:${VERSION}"; do
    if docker image inspect "$tag" > /dev/null 2>&1; then
        docker rmi "$tag"
        info "Removed image: $tag"
    else
        info "Image not found, skipping: $tag"
    fi
done

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