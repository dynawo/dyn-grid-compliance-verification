#!/bin/bash
#
# Writes the producer curves of the examples: the ones a producer delivers instead of a model,
# which is what `dycov validate -c` and `dycov performance -c` are verified with.
#
# They come from two places. The Model ones are the curves of a Model example, so they are taken
# from the run regenerate_reference_curves.sh already made. The Performance ones are the curves
# of a run in performance mode, which is made here.

set -o nounset -o noclobber
set -o errexit -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/models.sh"
source "$script_dir/curves_common.sh"

usage() {
    echo "Writes the producer curves of the Model and Performance examples."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -l, --launcher: Dynawo launcher script (default: dynawo.sh)"
    echo "  -o, --output:   working path of the runs and the anonymized curves"
    echo "                  (default: ../RegeneratedCurves)"
    echo "      --reuse:    anonymize the runs already in the working path instead of running"
    echo "                  the performance examples again"
    echo "  -h, --help:     display this help"
    echo
    echo "Notes:"
    echo "  • The Model producer curves are the curves of a Model example, so this stage reads"
    echo "    the run of regenerate_reference_curves.sh and must come after it."
    echo "  • The Performance ones are a run of their own, in performance mode, of the model each"
    echo "    family declares in models.sh."
    echo "  • Each directory is written whole: curves, dictionaries and their index. Nothing of a"
    echo "    previous regeneration survives in it."
}

launcher="dynawo.sh"
working_path="../RegeneratedCurves"
reuse=false

while (($#)); do
    case "$1" in
        -l | --launcher)    launcher=$2;     shift 2 ;;
        -o | --output)      working_path=$2; shift 2 ;;
        --reuse)            reuse=true;      shift ;;
        -h | --help)        usage; exit 0 ;;
        *)                  echo "$1: invalid option."; usage; exit 1 ;;
    esac
done

require_repo_root
examples_path="./examples"
results_path="$working_path/Results"
curves_path="$working_path/Curves"
user_config="$script_dir/release.ini"

[ -d "$curves_path/Model" ] ||
    fail "There are no anonymized Model curves in $curves_path: run
regenerate_reference_curves.sh first."
isolate_home "$working_path"

# 1. The Model producer curves: the curves of one of the Model examples, already anonymized.
for source in "${PRODUCER_CURVES_SOURCE[@]}"; do
    family="${source%%:*}"
    example="${source##*:}"
    log_msg "Producer curves of $family, from $example..."
    place_curves "$curves_path/Model/$example/Producer" \
        "$examples_path/Model/ProducerCurves/$family/Producer"
done

# 2. The Performance producer curves: a run in performance mode of the model each family names.
for source in "${PERFORMANCE_CURVES_SOURCE[@]}"; do
    family="${source%%:*}"
    model="$examples_path/${source##*:}"

    if [ "$reuse" = false ]; then
        log_msg "Running $model in performance mode, for the $family producer curves..."
        rm -rf "${results_path:?}/Performance/$family"
        dycov --user-config "$user_config" performance -l "$launcher" \
            -m "$model" -o "$results_path/Performance/$family" --testing
    fi

    log_msg "Anonymizing the $family performance curves..."
    anonymize_run "$results_path/Performance/$family" "$curves_path/Performance/$family" \
        "$user_config"
    place_curves "$curves_path/Performance/$family/Producer" \
        "$examples_path/Performance/ProducerCurves/$family/Producer"

    # What the anonymizer cannot write, because no curve carries it: the maximum injected
    # current the fault test of the fiche checks the reactive current against.
    python3 "$script_dir/example_inputs.py" imax --type "$family" \
        --producer "$examples_path/Performance/ProducerCurves/$family/Producer"
done

log_msg "Producer curves written."
