#!/bin/bash
#
# The whole cycle of one Model example: run it, check that it covered every test it declares,
# anonymize the results and write its reference curves.
#
# The example is the unit of work, so its curves are in place as soon as it is done — the rest
# of the regeneration does not have to finish for them to be usable — one that fails leaves the
# others alone, and one that needs doing again is one command.

set -o nounset -o noclobber
set -o errexit -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/curves_common.sh"

usage() {
    echo "Runs one Model example and writes its reference curves."
    echo "Usage: $0 [options] <family>/<example>"
    echo "Options:"
    echo "  -l, --launcher: Dynawo launcher script (default: dynawo.sh)"
    echo "  -o, --output:   working path for the run and the anonymized curves"
    echo "                  (default: ../RegeneratedCurves)"
    echo "      --reuse:    anonymize the run already in the working path instead of running"
    echo "                  the example again"
    echo "  -h, --help:     display this help"
    echo
    echo "Notes:"
    echo "  • The example runs in a home directory of its own, with release.ini next to this"
    echo "    script as its configuration, so that neither a PCS selection nor a modified"
    echo "    template of the machine running it can leave tests out of the release."
    echo "  • Its curves are written only once the run has covered every test the PCS of the"
    echo "    tool declare and every one the example declares for itself: half an example is"
    echo "    worse than none."
    echo "  • Fiche F16 is among the second kind, so regenerate_f16.sh has to have declared and"
    echo "    announced its tests first."
}

launcher="dynawo.sh"
working_path="../RegeneratedCurves"
reuse=false
example=""

while (($#)); do
    case "$1" in
        -l | --launcher)    launcher=$2;     shift 2 ;;
        -o | --output)      working_path=$2; shift 2 ;;
        --reuse)            reuse=true;      shift ;;
        -h | --help)        usage; exit 0 ;;
        -*)                 echo "$1: invalid option."; usage; exit 1 ;;
        *)                  example=$1;      shift ;;
    esac
done

[ -n "$example" ] || { echo "Name the example to regenerate."; usage; exit 1; }

require_repo_root
examples_path="./examples"
model_path="$examples_path/Model/$example/Dynawo"
reference_path="$examples_path/Model/$example/ReferenceCurves"
results_path="$working_path/Results/Model/$example"
curves_path="$working_path/Curves/Model/$example"
run_log="$working_path/Results/Model/$example.log"
user_config="$script_dir/release.ini"

[ -d "$model_path" ] || fail "There is no Model example at $model_path."
mkdir -p "$reference_path/Producer" "$(dirname "$run_log")"
isolate_home "$working_path"

# Whatever stops this example, the one who launched it has to see it stopped — and what stops
# it is usually a guard calling exit, which no ERR trap ever sees.
trap 'status=$?; [ "$status" -eq 0 ] || set_state "$example" failed' EXIT

# 1. Run it. Nothing the anonymizer does changes a simulation, so a run already made can be
#    reused when only the anonymizer's settings have changed.
if [ "$reuse" = true ]; then
    [ -d "$results_path" ] || fail "There is no run of $example to reuse in $results_path."
    log_msg "$example: reusing the run in $results_path"
else
    log_msg "$example: running..."
    set_state "$example" running
    rm -rf "${results_path:?}"
    start=$(date +%s)
    dycov --user-config "$user_config" validate -l "$launcher" \
        -m "$model_path" "$reference_path" -o "$results_path" --testing >| "$run_log" 2>&1 ||
        fail "$example: the run failed. See $run_log"
    log_msg "$example: ran in $(($(date +%s) - start))s"
fi

# 2. Check what ran before anything is written. A selection of PCS, of benchmarks or of
#    operating conditions anywhere would produce fewer tests, and the curves of the rest would
#    be written by nothing.
coverage=$(python3 "$script_dir/declared_tests.py" \
    --log "$run_log" --examples "$example" 2>&1) ||
    fail "$example: the run did not cover every test it declares. Nothing was written.
$coverage"
echo "$coverage"
not_simulated=$(printf '%s\n' "$coverage" | grep -c 'no curve for' || true)

# 3. Anonymize and write.
log_msg "$example: anonymizing..."
set_state "$example" anonymizing
anonymize_run "$results_path" "$curves_path" "$user_config"

for producer_path in "$curves_path"/*/; do
    [ -d "$producer_path" ] || fail "$example: anonymizing produced no producer directory."
    place_curves "${producer_path%/}" "$reference_path/$(basename "$producer_path")"
done

# What the anonymizer cannot say, because it only knows it anonymized a simulation: a declared
# test of Fiche F16 is a test recorded on site, and the tool reads that from its record.
declaration="$reference_path/F16Description.ini"
if [ -f "$declaration" ]; then
    python3 "$script_dir/example_inputs.py" field-measurements \
        --declaration "$declaration" --producer "$reference_path/Producer"
fi

written="$(find "$reference_path" -name '*.csv' | wc -l) curves"
[ "$not_simulated" -eq 0 ] || written="$written, $not_simulated not simulated"
set_state "$example" "done, $written"
log_msg "$example: done."
