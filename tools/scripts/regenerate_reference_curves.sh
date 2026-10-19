#!/bin/bash
#
# Writes the reference curves of every Model example, each one through its whole cycle: it is
# run, checked, anonymized and written before the next one is even started, so the curves of an
# example are usable as soon as it is done and a failure costs only its own example.
#
# It covers all of them, always: a partial set would ship a release whose examples do not match
# the tool that produced them. What it reports at the end is which ones did not make it.

set -o nounset -o noclobber
set -o errexit -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/models.sh"
source "$script_dir/curves_common.sh"

usage() {
    echo "Writes the reference curves of the Model examples, one whole example at a time."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -l, --launcher: Dynawo launcher script (default: dynawo.sh)"
    echo "  -o, --output:   working path for the runs and the anonymized curves"
    echo "                  (default: ../RegeneratedCurves)"
    echo "  -j, --jobs:     how many examples at a time (default: 4)"
    echo "      --reuse:    anonymize the runs already in the working path instead of running"
    echo "                  the examples again, for a change that only touches the anonymizer"
    echo "  -y, --yes:      replace a working path that holds a previous run without asking"
    echo "  -h, --help:     display this help"
    echo
    echo "Notes:"
    echo "  • Each example is a cycle of its own — run, check, anonymize, write — so its curves"
    echo "    are in place while the others are still running, and regenerate_one_example.sh"
    echo "    redoes just one of them."
    echo "  • A reference curve should not carry the oscillation of the simulation that produced"
    echo "    it, so it is removed with a $DERIPPLE_CUTOFF Hz filter, and the curves are reduced"
    echo "    to the samples that carry their shape."
    echo "  • An example writes nothing unless its run covered every test the PCS of the tool"
    echo "    declare and every one it declares for itself. Fiche F16 is among the second kind,"
    echo "    so regenerate_f16.sh has to have declared and announced its tests first."
}

launcher="dynawo.sh"
working_path="../RegeneratedCurves"
jobs=4
reuse=false
assume_yes=false

while (($#)); do
    case "$1" in
        -l | --launcher)    launcher=$2;     shift 2 ;;
        -o | --output)      working_path=$2; shift 2 ;;
        -j | --jobs)        jobs=$2;         shift 2 ;;
        --reuse)            reuse=true;      shift ;;
        -y | --yes)         assume_yes=true; shift ;;
        -h | --help)        usage; exit 0 ;;
        *)                  echo "$1: invalid option."; usage; exit 1 ;;
    esac
done

require_repo_root

if [ "$reuse" = false ]; then
    confirm_replacement "$working_path"
fi
mkdir -p "$working_path"

declare -a examples=("${MODEL_EXAMPLES_IEC[@]}" "${MODEL_EXAMPLES_WECC[@]}")
declare -a options=(-l "$launcher" -o "$working_path")
[ "$reuse" = true ] && options+=(--reuse)

log_msg "Regenerating ${#examples[@]} Model examples, $jobs at a time..."
failures="$working_path/failed_examples.txt"
:>| "$failures"

# Every example reports where it is, and with a console in front of us that is what is shown:
# the whole list at once, redrawn in place, instead of sixteen conversations interleaved.
DYCOV_STATE_DIR="$working_path/state"
export DYCOV_STATE_DIR
rm -rf "${DYCOV_STATE_DIR:?}"
mkdir -p "$DYCOV_STATE_DIR"
for example in "${examples[@]}"; do
    printf 'pending\n' >| "$DYCOV_STATE_DIR/${example//\//__}"
done

draw_states() {
    local example file state colour since now
    now=$(date +%s)
    for example in "${examples[@]}"; do
        file="$DYCOV_STATE_DIR/${example//\//__}"
        state=$(cat "$file" 2> /dev/null)
        case "$state" in
            done*)    colour="$GREEN" ;;
            failed)   colour="$RED" ;;
            pending)  colour="" ;;
            *)        # Still at it: say for how long, which is what tells a slow one from a
                      # stuck one.
                      colour="$GREEN"
                      since=$((now - $(stat -c %Y "$file" 2> /dev/null || echo "$now")))
                      state="$state ${since}s"
                      ;;
        esac
        printf "  %-46s ${colour}%s${NC}\033[K\n" "$example" "${state:-pending}"
    done
}

run_examples() {
    printf '%s\n' "${examples[@]}" \
        | xargs -P "$jobs" -I {} bash -c \
            "\"$script_dir/regenerate_one_example.sh\" \"\${@}\" {} || echo {} >> \"$failures\"" \
            _ "${options[@]}"
}

if [ -t 1 ]; then
    run_examples >| "$working_path/regeneration.log" 2>&1 &
    runner=$!
    echo "  (the chatter of each example goes to $working_path/regeneration.log)"
    draw_states
    while kill -0 "$runner" 2> /dev/null; do
        sleep 1
        printf '\033[%dA' "${#examples[@]}"
        draw_states
    done
    wait "$runner" || true
    printf '\033[%dA' "${#examples[@]}"
    draw_states
else
    run_examples
fi

incomplete=$(grep -l 'not simulated' "$DYCOV_STATE_DIR"/* 2> /dev/null | wc -l)
if [ "$incomplete" -gt 0 ]; then
    echo
    echo "Curves that no simulation produced, and so are not in the examples:"
    grep -h 'no curve for' "$working_path/regeneration.log" 2> /dev/null | sort -u | sed 's/^ *//'
fi

if [ -s "$failures" ]; then
    echo -e "${RED}These examples were not regenerated:${NC}" >&2
    sed 's/^/  /' "$failures" >&2
    fail "Their curves are the ones they already had. Run regenerate_one_example.sh on each."
fi
rm -f "$failures"

log_msg "Reference curves written for ${#examples[@]} Model examples."
