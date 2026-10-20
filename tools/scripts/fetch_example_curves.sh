#!/bin/bash
#
# Puts the curves of the examples in a clone that has none. They are not versioned: a release
# publishes them as the dycov_examples.zip asset, beside the Dynawo build, and this fetches them.
#
# The alternative is regenerate_curves.sh, which produces them from the tool itself and needs
# Dynawo and a few hours. This needs neither.

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

GREEN="\\033[1;32m"
RED="\\033[1;31m"
NC="\\033[0m"

ASSET="dycov_examples.zip"
RELEASES_URL="https://github.com/dynawo/dyn-grid-compliance-verification/releases/download"
LATEST_RELEASE_URL="https://api.github.com/repos/dynawo/dyn-grid-compliance-verification/releases/latest"

log_msg() {
    echo -e "${GREEN}$1${NC}"
}

fail() {
    echo -e "${RED}$1${NC}" >&2
    exit 1
}

usage() {
    echo "Fetches the curves of the examples from the asset of a release."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -r, --release: the release to take them from (default: the one this checkout"
    echo "                 descends from, as 'git describe --tags' reports it, or the latest"
    echo "                 one when it descends from none)"
    echo "  -h, --help:    display this help"
    echo
    echo "Notes:"
    echo "  • The curve directories are written where the examples expect them, and git ignores"
    echo "    them whole: they are a release artifact, not repository content."
    echo "  • Only the curve directories are taken from the asset, whole: everything else the"
    echo "    examples hold is versioned, and what the clone has is what its checkout says."
    echo "  • The release the curves come from is recorded in examples/.curves-release, which"
    echo "    is what the integration tests read to tell you which curves they ran on."
}

release=""

while (($#)); do
    case "$1" in
        -r | --release)  release=$2; shift 2 ;;
        -h | --help)     usage; exit 0 ;;
        *)               echo "$1: invalid option."; usage; exit 1 ;;
    esac
done

[ -d "./examples/Model" ] || fail "Run this from the root of the repository."

for command in curl unzip; do
    command -v "$command" > /dev/null || fail "Required command not found: '$command'."
done

# The curves that belong to a checkout are the ones its release shipped: anything else reports
# verdicts that have nothing to do with the code being read. A checkout that descends from no
# release — a shallow clone, a branch cut before the first tag — takes those of the latest one.
if [ -z "$release" ]; then
    release=$(git describe --tags --abbrev=0 2> /dev/null) || release=""
fi
if [ -z "$release" ]; then
    release=$(curl -sS -L --fail "$LATEST_RELEASE_URL" |
        sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -1) ||
        fail "This checkout descends from no release and the latest one could not be read:
name one with --release."
    [ -n "$release" ] || fail "The latest release could not be read: name one with --release."
fi

url="$RELEASES_URL/$release/$ASSET"
download_path=$(mktemp -d)
trap 'rm -rf "$download_path"' EXIT

log_msg "Fetching the curves of release $release..."
curl -sS -L --fail -o "$download_path/$ASSET" "$url" || fail "Release $release publishes no $ASSET.
Releases before the curves became an asset carry them in the repository instead, and a release
that should publish them and does not is a release to report. To produce them yourself:
    tools/scripts/regenerate_curves.sh"

unzip -tq "$download_path/$ASSET" > /dev/null || fail "The downloaded $ASSET is not readable."
unzip -q "$download_path/$ASSET" -d "$download_path/unpacked"

[ -d "$download_path/unpacked/examples" ] ||
    fail "The asset of release $release does not hold an examples directory."

# A curve directory arrives whole, as the regeneration writes it: the curves, the dictionaries
# that describe them, their index and the declarations beside them. Whatever was there goes
# first, so a test that is no longer recorded leaves nothing behind.
directories=0
while IFS= read -r source_directory; do
    target_directory="./examples/${source_directory#"$download_path/unpacked/examples/"}"
    rm -rf "${target_directory:?}"
    mkdir -p "$(dirname "$target_directory")"
    cp -a "$source_directory" "$target_directory"
    directories=$((directories + 1))
done < <(find "$download_path/unpacked/examples" -type d \
    \( -name ReferenceCurves -o -name ProducerCurves \) | sort)

curves=$(find ./examples -name "*.csv" | wc -l)
[ "$curves" -gt 0 ] || fail "The asset of release $release holds no curve."

echo "$release" > ./examples/.curves-release
log_msg "$curves curves in $directories directories, from release $release."
