#!/bin/bash
#
# Writes the producer declaration of every curve directory of the examples.
#
# A delivery of curves has no model, so the producer states its own magnitudes: that is what
# Producer.ini is for, and it is not versioned either, because it sits inside a curve directory.
# Each one is written from the model whose curves the directory ships, named in models.sh, plus
# the values no model states — the apparent power — which are in example_inputs.ini.

set -o nounset -o noclobber
set -o errexit -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/models.sh"
source "$script_dir/curves_common.sh"

usage() {
    echo "Writes the Producer.ini of every curve directory of the examples."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -h, --help:     display this help"
    echo
    echo "Notes:"
    echo "  • The producer of a curve directory is the producer of the example its curves come"
    echo "    from: models.sh names the pair, and nothing here chooses it."
    echo "  • The parameters of the Dynawo model do not travel — there is no model on this side —"
    echo "    and what the model does not state, the apparent power of each zone, is read from"
    echo "    example_inputs.ini."
    echo "  • The declaration of a Model producer names its zone, because the curves of Zone 1 and"
    echo "    of Zone 3 are those of different producers; the ones of Performance do not."
}

while (($#)); do
    case "$1" in
        -h | --help)        usage; exit 0 ;;
        *)                  echo "$1: invalid option."; usage; exit 1 ;;
    esac
done

require_repo_root
examples_path="./examples"
write_inputs="python3 $script_dir/example_inputs.py"

# The producer curves of a Model family are the curves of one of its examples, zone by zone.
for source in "${PRODUCER_CURVES_SOURCE[@]}"; do
    family="${source%%:*}"
    example="${source##*:}"
    for zone in Zone1 Zone3; do
        model="$examples_path/Model/$example/Dynawo/$zone"
        [ -d "$model" ] || fail "$example has no $zone model to declare its producer from."
        $write_inputs producer --model "$model" --type "$family" --zone "$zone" \
            --output "$examples_path/Model/ProducerCurves/$family/$zone/Producer.ini"
        log_msg "  $family $zone declared from $model"
    done
done

# The producer curves of a Performance family are those of a run in performance mode.
for source in "${PERFORMANCE_CURVES_SOURCE[@]}"; do
    family="${source%%:*}"
    model="$examples_path/${source##*:}"
    [ -d "$model" ] || fail "$family names $model, which does not exist."
    $write_inputs producer --model "$model" --type "$family" \
        --output "$examples_path/Performance/ProducerCurves/$family/Producer.ini"
    log_msg "  $family declared from $model"
done

log_msg "Producer declarations written."
