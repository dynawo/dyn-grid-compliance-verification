#!/bin/bash
#
# What every stage of the regeneration shares: where things go, how a run is anonymized, and how
# a finished curve directory is put in place.
#
# Source it; do not run it.

GREEN="\\033[1;32m"
RED="\\033[1;31m"
NC="\\033[0m"

# The release ships curves that look like measurements and are no larger than they need to be.
# These are the values that shape them, each measured on the examples rather than chosen:
#   - nothing is de-rippled, against the anonymizer's default: on the examples the de-ripple
#     only caught responses of the models, never an oscillation of the solver;
#   - this epsilon keeps a fiftieth of the samples, and 343 of the 386 curves under a tenth,
#     while no compared magnitude moves by more than 0.004 pu where the test looks and 0.001
#     away from it, against tolerances of 0.08 and 0.002. What resists it is not the epsilon's
#     doing: a curve that never settles carries shape in every sample, and the worst of them
#     still keeps seven tenths.
NOISE_STD=0.01
NOISE_FREQUENCY=15.0
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

# The revision of the DTR the regeneration follows: the one asked for, checked against the ones
# the tool implements, or the one release.ini names.
dtr_revision() {
    python3 "$script_dir/example_inputs.py" revision ${1:+--dtr "$1"}
}

# The configuration every run of the regeneration reads: release.ini, naming the revision of the
# DTR it follows. Another revision is written into a copy of it in the working path, so that
# asking for one changes nothing in the repository. Each copy is put in place whole, because the
# examples of a stage run at the same time and read it as it is written.
run_configuration() {
    local working_path="$1"
    local revision="$2"
    local release="$script_dir/release.ini"

    if [ "$revision" = "$(dtr_revision)" ]; then
        echo "$release"
        return 0
    fi
    mkdir -p "$working_path"
    local configuration
    configuration="$(cd "$working_path" && pwd)/release_$revision.ini"
    local draft
    draft=$(mktemp "$configuration.XXXXXX")
    sed "s/^current *=.*/current = $revision/" "$release" >| "$draft"
    mv -f "$draft" "$configuration"
    echo "$configuration"
}

# The revision of the DTR a run followed, as its log says it.
revision_of_run() {
    sed -n 's/.*Validating against the DTR revision \([0-9A-Za-z_]*\)\..*/\1/p' "$1" | head -n 1
}

# The revision of the DTR the runs to reuse followed, from their logs. A set of curves is the set
# of one revision, so runs that followed several cannot be reused together.
revision_of_runs() {
    local revision=""
    local log followed
    for log in "$@"; do
        [ -f "$log" ] || fail "There is no log of the run to reuse in $log."
        followed=$(revision_of_run "$log")
        [ -n "$followed" ] || fail "The log $log does not say which revision of the DTR it ran."
        [ -z "$revision" ] || [ "$followed" = "$revision" ] ||
            fail "The runs to reuse followed the DTR revisions $revision and $followed: run them
again instead of reusing them."
        revision=$followed
    done
    echo "$revision"
}

# The revision of the DTR a regeneration that reuses runs follows: the one the runs followed,
# which has to be the one asked for when one is.
revision_to_reuse() {
    local requested="$1"
    shift
    local followed
    followed=$(revision_of_runs "$@")
    [ -z "$requested" ] || [ "$(dtr_revision "$requested")" = "$followed" ] ||
        fail "The runs to reuse followed the DTR revision $followed, not $requested: run them
again instead of reusing them."
    echo "$followed"
}

# The curves of a release must not depend on the machine that produced them, and the tool reads
# its configuration and its PCS templates from the home directory: a selection of PCS there, or
# a modified template, would leave tests out without saying so. A home of its own removes both.
isolate_home() {
    HOME="$(cd "$1" && pwd)/home"
    export HOME
    mkdir -p "$HOME"
}

# Where each example says how it is doing, so that whoever launched them all can show it. The
# launcher sets it; a single example run by hand has nowhere to report and does not need one.
set_state() {
    [ -n "${DYCOV_STATE_DIR:-}" ] || return 0
    printf '%s\n' "$2" >| "$DYCOV_STATE_DIR/${1//\//__}"
}

anonymize_run() {
    local results="$1"
    local output="$2"
    local user_config="$3"

    [ -d "$results" ] || fail "There is no run to anonymize in $results."
    rm -rf "${output:?}"
    dycov --user-config "$user_config" anonymize \
        --noisestd "$NOISE_STD" --frequency "$NOISE_FREQUENCY" \
        --deripple 0 --compression "$COMPRESSION" \
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
