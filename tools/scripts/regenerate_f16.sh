#!/bin/bash
#
# Declares the on-site tests of the DTR Fiche F16 in every Model example, and announces the
# delivery of the records that are about to be made of them.
#
# The fiche fixes no test, so a producer declares the ones it recorded and delivers the records
# with them. The examples have neither, so both are made: the declaration is written from
# example_inputs.ini and from the template of the declaration, as the revision of the DTR writes
# it, and the records are the tool's own simulations of the tests it declares, anonymized as
# measurements, exactly as the other curves of the examples are.
#
# This is the first stage of the regeneration, and it cannot be any later: the run simulates the
# tests the declaration names, which is what their records are made of, so the declaration has
# to be in place before it. The delivery is announced by its index alone; the run simulates a
# declared test whether or not its record exists, and the anonymized run writes the records.

set -o nounset -o noclobber
set -o errexit -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/models.sh"
source "$script_dir/curves_common.sh"

usage() {
    echo "Declares the tests of the DTR Fiche F16 in every Model example and announces the"
    echo "delivery of their records, so that the regeneration run simulates them."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "      --dtr:      revision of the DTR the curves follow, as YYYYMMDD (default: the one"
    echo "                  release.ini names)"
    echo "  -h, --help:     display this help"
    echo
    echo "Notes:"
    echo "  • It must run before regenerate_reference_curves.sh: what makes the tool run a"
    echo "    test of Fiche F16 is its declaration, so it goes in first and the run then"
    echo "    produces the curves the record is made of."
    echo "  • Which tests are declared, and their steps, is in example_inputs.ini. The choice is"
    echo "    the same for every example, because it is invented for them: the fiche selects no"
    echo "    test of its own. The power levels, the checks and the figures are the ones the fiche"
    echo "    fixes, as the revision of the DTR writes the template of the declaration."
    echo "  • The declaration is written where the tool reads it and where a producer delivering"
    echo "    records puts it, next to them, under ReferenceCurves."
}

dtr=""

while (($#)); do
    case "$1" in
        --dtr)              dtr=$2;          shift 2 ;;
        -h | --help)        usage; exit 0 ;;
        *)                  echo "$1: invalid option."; usage; exit 1 ;;
    esac
done

require_repo_root
examples_path="./examples"
write_inputs="python3 $script_dir/example_inputs.py"
revision=$(dtr_revision "$dtr")

declare -a examples=("${MODEL_EXAMPLES_IEC[@]}" "${MODEL_EXAMPLES_WECC[@]}" "${MODEL_EXAMPLES_GFM[@]}")

for example in "${examples[@]}"; do
    case "$example" in
        BESS/*) family=BESS ;;
        *)      family=PPM ;;
    esac
    reference_path="$examples_path/Model/$example/ReferenceCurves"
    declaration="$reference_path/F16Description.ini"

    log_msg "Declaring the F16 tests of $example ($family)..."
    $write_inputs f16 --type "$family" --dtr "$revision" --output "$declaration"
    $write_inputs announce --reference "$reference_path" \
        --model "$examples_path/Model/$example/Dynawo" --type "$family"
done

log_msg "F16 declared and announced in ${#examples[@]} Model examples, for the DTR revision $revision."
