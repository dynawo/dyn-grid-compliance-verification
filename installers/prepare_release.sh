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
#   - dycov_examples.zip            (the examples with the curves of this release)
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

# The examples, with the curves this release ships. They are not versioned: this is how they
# reach the user, and linux_install.sh downloads it as it downloads the Dynawo build.
EXAMPLES_ZIP_NAME="dycov_examples.zip"

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

# Version without 'v', as setuptools_scm reports it
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

    # Git-ignored leftovers under examples/ are invisible to the check above, and a
    # stale Results/ from a local run means the examples on disk are not what the
    # release describes. The curve directories are ignored by design — they ship as
    # $EXAMPLES_ZIP_NAME — so they are the one thing that belongs there.
    STALE_EXAMPLES=$(git status --porcelain --ignored -- examples | grep "^!! " \
        | grep -vE '/(ReferenceCurves|ProducerCurves)/|/\.curves-release$' || true)
    if [[ -n "$STALE_EXAMPLES" ]]; then
        echo "$STALE_EXAMPLES" >&2
        error "Git-ignored artifacts found under examples/ (see above). Remove them before releasing."
    fi

    # And the other half of the same coin: the curves are not in the commit, so nothing else
    # would notice a release built from a tree where they were never generated. A directory
    # that holds dictionaries is a directory whose curves ship.
    CURVELESS=$(find examples -name '*.dict' -printf '%h\n' | sort -u \
        | while read -r directory; do
              compgen -G "$directory/*.csv" > /dev/null || echo "$directory"
          done)
    if [[ -n "$CURVELESS" ]]; then
        echo "$CURVELESS" >&2
        error "No curves under the directories above. Run tools/scripts/regenerate_curves.sh."
    fi

    info "Git state OK:"
    info " - Tag: $CURRENT_TAG"
    info " - Commit: $(git rev-parse --short HEAD)"
fi

###############################################################################
# Validate expected repo files
###############################################################################
LINUX_INSTALL="$REPO_ROOT/installers/linux_install.sh"
BUILD_SH="$REPO_ROOT/installers/docker/build.sh"
EXPORT_SH="$REPO_ROOT/installers/docker/export_image.sh"
IMPORT_SH="$REPO_ROOT/installers/docker/import_image.sh"
RUN_SH="$REPO_ROOT/installers/docker/run_dycov_docker.sh"
IMPORT_WSL_BAT="$REPO_ROOT/installers/wsl/import_wsl.bat"
IMPORT_WSL_PS1="$REPO_ROOT/installers/wsl/import_wsl.ps1"
RUN_WSL_PS1="$REPO_ROOT/installers/wsl/run_dycov_wsl.ps1"

for f in "$LINUX_INSTALL" "$BUILD_SH" "$EXPORT_SH" "$IMPORT_SH" "$RUN_SH" \
          "$IMPORT_WSL_BAT" "$IMPORT_WSL_PS1" "$RUN_WSL_PS1"; do
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
# Step 1b — Generate the examples ZIP, curves included
###############################################################################
step "Step 1b: Generating $EXAMPLES_ZIP_NAME..."

EXAMPLES_ZIP="$OUTPUT_DIR/$EXAMPLES_ZIP_NAME"
EXAMPLES_STAGING=$(mktemp -d)

# Two sources, and neither alone is right: Git carries the tracked tree, so no local artifact
# can reach the asset, and the working tree carries the curve directories, which Git no longer
# holds at all — not the curves, not their dictionaries, not the declarations beside them.
cd "$REPO_ROOT"
git archive HEAD examples | tar -x -C "$EXAMPLES_STAGING"
find examples -type d \( -name ReferenceCurves -o -name ProducerCurves \) \
    -exec cp -a --parents {} "$EXAMPLES_STAGING" \;

cd "$EXAMPLES_STAGING"
zip -qr "$EXAMPLES_ZIP" examples
cd "$REPO_ROOT"
rm -rf "$EXAMPLES_STAGING"
info "$EXAMPLES_ZIP_NAME generated ($(du -h "$EXAMPLES_ZIP" | cut -f1))."

###############################################################################
# Step 2 — Generate updated linux_install.sh in output dir
###############################################################################
step "Step 2: Generating updated linux_install.sh..."

DYNAWO_SHA256=$(sha256sum "$DYNAWO_ZIP" | cut -d' ' -f1)
EXAMPLES_SHA256=$(sha256sum "$EXAMPLES_ZIP" | cut -d' ' -f1)
info "SHA256: $DYNAWO_SHA256"
info "SHA256: $EXAMPLES_SHA256"

LINUX_INSTALL_OUT="$OUTPUT_DIR/linux_install.sh"
cp "$LINUX_INSTALL" "$LINUX_INSTALL_OUT"

# Remove the git fetch --tags line (we don't want to fetch tags in the release script)
sed -i '/^[[:space:]]*cd "\$TMP_LOCAL_REPO"[[:space:]]*$/d' "$LINUX_INSTALL_OUT"
sed -i '/git fetch .*--tags/d' "$LINUX_INSTALL_OUT"

# Update TARGET_BRANCH (with 'v' prefix, matches the git tag)
sed -i -E "s|^TARGET_BRANCH=.*|TARGET_BRANCH=\"${VERSION}\"|" "$LINUX_INSTALL_OUT"

# Update the checksums with those of the zips generated in Steps 1 and 1b
sed -i -E "s|^DYNAWO_SHA256SUM=.*|DYNAWO_SHA256SUM=\"${DYNAWO_SHA256}\"|" "$LINUX_INSTALL_OUT"
sed -i -E "s|^EXAMPLES_SHA256SUM=.*|EXAMPLES_SHA256SUM=\"${EXAMPLES_SHA256}\"|" "$LINUX_INSTALL_OUT"

info "linux_install.sh updated."
info "--- Relevant lines ---"
grep -E "^(TARGET_BRANCH|DYNAWO_SHA256SUM|EXAMPLES_SHA256SUM)=" "$LINUX_INSTALL_OUT"
echo "----------------------"

###############################################################################
# Step 3 — Build the documentation manuals
###############################################################################
step "Step 3: Building documentation manuals..."

MANUAL_BUILD_DIR="$REPO_ROOT/docs/manual/build"

# Clean any previous build
rm -rf "$MANUAL_BUILD_DIR"

# Install sphinx AND dycov in a temporary venv and build.
# helps.py invokes the `dycov` CLI (dycov --help, dycov generate --help, ...) to
# generate the command help pages, so dycov must be installed in the venv. This
# keeps the manual build self-contained instead of relying on a dev environment
# having dycov on PATH. The version is forced here so the manual quotes the release
# version even if the doc build leaves the tree dirty.
uv venv "$REPO_ROOT/.manual_venv" --python 3.13 --quiet
source "$REPO_ROOT/.manual_venv/bin/activate"
uv pip install -q sphinx
SETUPTOOLS_SCM_PRETEND_VERSION_FOR_dycov=${VERSION_PLAIN} \
    uv pip install -q "$REPO_ROOT"
cd "$REPO_ROOT/docs/manual"
MANUAL_LOG="$OUTPUT_DIR/manual_build.log"
make latexpdf > "$MANUAL_LOG" 2>&1 < /dev/null \
    || error "The manual PDF build failed. See $MANUAL_LOG"
make html >> "$MANUAL_LOG" 2>&1 < /dev/null \
    || error "The manual HTML build failed. See $MANUAL_LOG"
rm -f "$MANUAL_LOG"
deactivate
rm -rf "$REPO_ROOT/.manual_venv"

info "Manuals built:"
info " - HTML: $MANUAL_BUILD_DIR/html"
info " - PDF:  $MANUAL_BUILD_DIR/latex/dycov.pdf"

###############################################################################
# Step 4 — Build Docker image
###############################################################################
step "Step 4: Building Docker image..."

cd "$REPO_ROOT/installers/docker"
bash build.sh "$VERSION" "$DYNAWO_DIR" ${DRY_RUN:+--dry-run}
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

mv "$RAW_IMAGE"       "$OUTPUT_DIR/dycov_rawimage.tar.gz"
cp "$IMPORT_SH"       "$OUTPUT_DIR/import_image.sh"
cp "$RUN_SH"          "$OUTPUT_DIR/run_dycov_docker.sh"
cp "$IMPORT_WSL_BAT"  "$OUTPUT_DIR/import_wsl.bat"
cp "$IMPORT_WSL_PS1"  "$OUTPUT_DIR/import_wsl.ps1"
cp "$RUN_WSL_PS1"     "$OUTPUT_DIR/run_dycov_wsl.ps1"

info "All artifacts ready."

###############################################################################
# Step 7 — Remove Docker images
###############################################################################
step "Step 7: Removing Docker images..."

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
warn "The loose *.sh artifacts (import_image.sh, run_dycov_docker.sh) lose their exec bit"
warn "when downloaded from GitHub. End users must run 'chmod +x' before executing them;"
warn "this is documented in docs/installation/using_the_provided_image.md (section 3.2) and"
warn "in the manual. linux_install.sh does not need it: the docs pipe it straight into bash."
echo ""