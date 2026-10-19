#!/bin/bash
#
# What every stage of the regeneration shares: where things go, how a run is anonymized, and how
# a finished curve directory is put in place.
#
# Source it; do not run it.

GREEN="\\033[1;32m"
RED="\\033[1;31m"
NC="\\033[0m"

# The release ships curves that look like measurements, without the oscillation of the
# simulation that produced them, and no larger than they need to be. These are the values that
# shape them, each measured on the examples rather than chosen:
#   - the oscillation sits between 12 and 17 Hz, and only a cut-off this low removes it;
#   - this epsilon keeps a fiftieth of the samples, and 343 of the 386 curves under a tenth,
#     while no compared magnitude moves by more than 0.004 pu where the test looks and 0.001
#     away from it, against tolerances of 0.08 and 0.002. What resists it is not the epsilon's
#     doing: a curve that never settles carries shape in every sample, and the worst of them
#     still keeps seven tenths.
NOISE_STD=0.01
NOISE_FREQUENCY=15.0
DERIPPLE_CUTOFF=5.0
COMPRESSION=0.00005

log_msg() {
    echo -e "${GREEN}$1${NC}"
}

fail() {
    echo -e "${RED}$1${NC}" >&2
    exit 1
}

require_repo_root() {
    [ -d "./examples/Model" ] || fail "Run this from the root of the repository."
}

# Replacing the results of a previous run is asked for, never assumed: a run of every example
# takes too long to lose by accident.
confirm_replacement() {
    [ -d "$1" ] && [ -n "$(ls -A "$1")" ] || return 0

    local answer=""
    if [ "${assume_yes:-false}" = true ]; then
        rm -rf "${1:?}"
        return 0
    fi
    [ -t 0 ] || fail "$1 holds a previous run: remove it, choose another output path, or pass -y."
    printf "%b" "${RED}$1 holds a previous run.${NC} Replace it? [y/N] "
    read -r answer || true
    [[ "$answer" == [yY] ]] || fail "Nothing was replaced."
    rm -rf "${1:?}"
}

# The curves of a release must not depend on the machine that produced them, and the tool reads
# its configuration and its PCS templates from the home directory: a selection of PCS there, or
# a modified template, would leave tests out without saying so. A home of its own removes both.
isolate_home() {
    HOME="$(cd "$1" && pwd)/home"
    export HOME
    mkdir -p "$HOME"
}

anonymize_run() {
    local results="$1"
    local output="$2"
    local user_config="$3"

    [ -d "$results" ] || fail "There is no run to anonymize in $results."
    rm -rf "${output:?}"
    dycov --user-config "$user_config" anonymize \
        --noisestd "$NOISE_STD" --frequency "$NOISE_FREQUENCY" \
        --deripple "$DERIPPLE_CUTOFF" --compression "$COMPRESSION" \
        --results "$results" --output "$output"
}

# A curve directory is written whole: the curves, the dictionaries that describe them and the
# index of both. Nothing of a previous regeneration survives, so a test that is no longer run
# leaves nothing behind.
place_curves() {
    local source_path="$1"
    local target_path="$2"

    compgen -G "$source_path/*.csv" > /dev/null || fail "$source_path holds no curve."
    rm -rf "${target_path:?}"
    mkdir -p "$target_path"
    cp -a "$source_path/." "$target_path/"
    log_msg "  $(find "$target_path" -name '*.csv' | wc -l) curves in $target_path"
}
