#!/bin/bash
#
# Regenerates everything the curve directories of the examples hold, which is the last step
# before a release. They are not versioned: this writes them, and installers/prepare_release.sh
# packs them as the dycov_examples.zip asset of the release, which is how they reach the user.
#
# The work is four stages, each its own script and each runnable on its own. The order is not a
# matter of taste:
#
#   1. regenerate_f16.sh                the declared tests of the DTR Fiche F16
#   2. regenerate_producer_inis.sh      the producer each curve directory declares
#   3. regenerate_reference_curves.sh   the reference curves of every Model example
#   4. regenerate_producer_curves.sh    the curves a producer delivers instead of a model
#
# A declared test of Fiche F16 is run only where its record exists, so stage 1 declares it and
# announces the record before anything runs; stage 3 then simulates every test, F16 among them,
# which is what its record is made of. The producer curves of the Model examples are the curves
# of a Model example, so stage 4 reads the run of stage 3.

set -o nounset -o noclobber
set -o errexit -o pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/curves_common.sh"

usage() {
    echo "Regenerates every curve directory of the examples, whole."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -l, --launcher: Dynawo launcher script (default: dynawo.sh)"
    echo "  -o, --output:   working path for the runs and the anonymized curves"
    echo "                  (default: ../RegeneratedCurves)"
    echo "  -j, --jobs:     max parallel runs (default: 4)"
    echo "      --reuse:    anonymize the runs already in the working path instead of running"
    echo "                  the examples again, for a change that only touches the anonymizer"
    echo "  -y, --yes:      replace a working path that holds a previous run without asking,"
    echo "                  which is what a release pipeline needs"
    echo "  -h, --help:     display this help"
    echo
    echo "Notes:"
    echo "  • It runs every test of every example, so it is the longest step of a release."
    echo "  • Each stage is a script of its own and takes the same options; run '--help' on any"
    echo "    of them for what it does:"
    echo "      regenerate_producer_inis.sh, regenerate_reference_curves.sh,"
    echo "      regenerate_producer_curves.sh, regenerate_f16.sh"
    echo "  • Nothing it writes is versioned: the curve directories of the examples are ignored"
    echo "    whole, and they travel as the asset of the release."
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

declare -a reuse_option=()
[ "$reuse" = true ] && reuse_option=(--reuse)
declare -a yes_option=()
[ "$assume_yes" = true ] && yes_option=(-y)

log_msg "1/4 — the declared tests of the DTR Fiche F16"
"$script_dir/regenerate_f16.sh"

log_msg "2/4 — the producer each curve directory declares"
"$script_dir/regenerate_producer_inis.sh"

log_msg "3/4 — the reference curves of the Model examples"
"$script_dir/regenerate_reference_curves.sh" -l "$launcher" -o "$working_path" -j "$jobs" \
    "${reuse_option[@]}" "${yes_option[@]}"

log_msg "4/4 — the curves a producer delivers instead of a model"
"$script_dir/regenerate_producer_curves.sh" -l "$launcher" -o "$working_path" \
    "${reuse_option[@]}"

# Where these curves come from. They are not versioned, so nothing else records it, and a test
# that asserts anything of them is asserting it of this particular set.
echo "the working tree at $(git rev-parse --short HEAD)" >| "./examples/.curves-release"

log_msg "Done. The curve directories are written whole and none of them is versioned: what ships
them is the dycov_examples.zip asset that installers/prepare_release.sh packs."
