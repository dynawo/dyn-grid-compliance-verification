#!/bin/bash
#
# Regenerates the curves shipped with the Model examples, which is the last step before a
# release: runs every example, anonymizes its results, and replaces the curves in the repository.
#
# It regenerates all of them, always: a partial set would ship a release whose examples do not
# match the tool that produced them.

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

GREEN="\\033[1;32m"
RED="\\033[1;31m"
NC="\\033[0m"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/models.sh"

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

# Replacing the results of a previous run is asked for, never assumed: a run of every example
# takes too long to lose by accident.
confirm_replacement() {
    [ -d "$1" ] && [ -n "$(ls -A "$1")" ] || return 0

    local answer=""
    [ -t 0 ] || fail "$1 holds a previous run: remove it, or choose another output path."
    printf "%b" "${RED}$1 holds a previous run.${NC} Replace it? [y/N] "
    read -r answer || true
    [[ "$answer" == [yY] ]] || fail "Nothing was replaced."
    rm -rf "${1:?}"
}

usage() {
    echo "Regenerates every reference and producer curve of the Model examples."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -l, --launcher: Dynawo launcher script (default: dynawo.sh)"
    echo "  -o, --output:   working path for the runs and the anonymized curves"
    echo "                  (default: ../RegeneratedCurves)"
    echo "  -j, --jobs:     max parallel runs (default: 4)"
    echo "      --reuse:    anonymize the run already in the working path instead of running"
    echo "                  the examples again, for a change that only touches the anonymizer"
    echo "  -h, --help:     display this help"
    echo
    echo "Notes:"
    echo "  • Every example runs in a home directory of its own, with release.ini next to this"
    echo "    script as its configuration, so that neither a PCS selection nor a modified"
    echo "    template of the machine running it can leave tests out of the release."
    echo "  • A reference curve should not carry the oscillation of the simulation that produced"
    echo "    it, so it is removed with a $DERIPPLE_CUTOFF Hz filter, and the curves are reduced"
    echo "    to the samples that carry their shape."
    echo "  • The curves of the repository are replaced only once every example is anonymized,"
    echo "    so a failed run leaves them untouched. Every curve of a directory is removed before"
    echo "    the new ones are copied, so a test that is no longer run leaves none behind."
    echo "  • The dictionaries stay; only the event they declare is brought up to date."
    echo "  • A working path that holds a previous run is replaced only after confirmation."
}

launcher="dynawo.sh"
working_path="../RegeneratedCurves"
jobs=4
reuse=false

while (($#)); do
    case "$1" in
        -l | --launcher)    launcher=$2;     shift 2 ;;
        -o | --output)      working_path=$2; shift 2 ;;
        -j | --jobs)        jobs=$2;         shift 2 ;;
        --reuse)            reuse=true;      shift ;;
        -h | --help)        usage; exit 0 ;;
        *)                  echo "$1: invalid option."; usage; exit 1 ;;
    esac
done

examples_path="./examples"
[ -d "$examples_path/Model" ] || fail "Run this from the root of the repository."

results_path="$working_path/Results"
curves_path="$working_path/Curves"
if [ "$reuse" = false ]; then
    confirm_replacement "$working_path"
fi
mkdir -p "$working_path"

user_config="$script_dir/release.ini"

# The curves of a release must not depend on the machine that produced them, and the tool reads
# its configuration and its PCS templates from the home directory: a selection of PCS there, or
# a modified template, would leave tests out without saying so. A home of its own removes both.
export HOME="$(cd "$working_path" && pwd)/home"
mkdir -p "$HOME"

declare -a examples=("${MODEL_EXAMPLES_IEC[@]}" "${MODEL_EXAMPLES_WECC[@]}")

# 1. Run every example, which is what writes curves_calculated.csv and its simulation record.
#    Nothing the anonymizer does changes a simulation, so a run already made can be reused.
if [ "$reuse" = true ]; then
    log_msg "Reusing the run of ${#examples[@]} Model examples in $results_path..."
    [ -f "$results_path/test_tool.log" ] || fail "There is no run to reuse in $results_path."
else
    log_msg "Running the ${#examples[@]} Model examples..."
    "$script_dir/test_tool.sh" -v -l "$launcher" -e "$examples_path" -o "$results_path" \
        -j "$jobs" --user-config "$user_config"
fi

# 1b. Count what ran. A selection of PCS, of benchmarks or of operating conditions anywhere
#     would produce fewer tests, and the curves of the rest would be replaced by nothing.
python3 - "$results_path/test_tool.log" "${examples[@]}" << 'PYCODE' ||
import configparser
import re
import sys
from collections import defaultdict
from pathlib import Path

TEMPLATES = Path("src/dycov/templates/PCS/model")
MODEL_DIR = re.compile(r"\*\*\*Model dir: examples/Model/(.+?)/Dynawo\*\*\*")

log_path, examples = Path(sys.argv[1]), sys.argv[2:]


def declared_tests(family: str) -> set:
    """The operating conditions the PCS of a family declare, which is what must run."""
    declared = set()
    for description in sorted((TEMPLATES / family).glob("[!.]*/PCSDescription.ini")):
        pcs_config = configparser.ConfigParser(inline_comment_prefixes=("#",))
        pcs_config.optionxform = str
        pcs_config.read(description)
        for pcs, benchmarks in pcs_config.items("PCS-Benchmarks"):
            for benchmark in benchmarks.split(","):
                conditions = pcs_config.get("PCS-OperatingConditions", f"{pcs}.{benchmark}")
                declared.update((pcs, benchmark, oc) for oc in conditions.split(","))
    return declared


def executed_tests(log_path: Path) -> dict:
    """The tests each example reports. An example whose zones are split among producers
    reports the same test once per producer, so they are gathered as a set."""
    executed = defaultdict(set)
    example = None
    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        model_dir = MODEL_DIR.search(line)
        if model_dir:
            example = model_dir.group(1)
        elif example and line.startswith("Producer") and "PCS_RTE-" in line:
            executed[example].add(tuple(line.split()[1:4]))
    return executed


executed = executed_tests(log_path)
declared_total = covered_total = 0
missing = {}
for example in examples:
    declared = declared_tests("BESS" if example.startswith("BESS/") else "PPM")
    declared_total += len(declared)
    covered_total += len(declared & executed[example])
    if declared - executed[example]:
        missing[example] = sorted(declared - executed[example])

print(f"Tests: {covered_total} executed, {declared_total} declared by the PCS of the examples.")
for example, tests in missing.items():
    print(f"  {example} never ran " + ", ".join(".".join(test) for test in tests))
sys.exit(1 if missing else 0)
PYCODE
    fail "The run did not cover every test: something is selecting what to verify. The curves
of the repository are left untouched."

# 2. Anonymize the results of each example.
for example in "${examples[@]}"; do
    [ -d "$results_path/Model/$example" ] || fail "The run left no results for $example."
    log_msg "Anonymizing $example..."
    rm -rf "${curves_path:?}/Model/$example"
    dycov --user-config "$user_config" anonymize \
        --noisestd "$NOISE_STD" --frequency "$NOISE_FREQUENCY" \
        --deripple "$DERIPPLE_CUTOFF" --compression "$COMPRESSION" \
        --results "$results_path/Model/$example" --output "$curves_path/Model/$example"
done

# 3. Check every replacement before touching the repository: the curves that ship are the
#    reference of the release, and half a regeneration is worse than none.
declare -a replacements=()
for example in "${examples[@]}"; do
    for producer_path in "$curves_path/Model/$example"/*/; do
        [ -d "$producer_path" ] || fail "Anonymizing $example produced no producer directory."
        producer=$(basename "$producer_path")
        target_path="$examples_path/Model/$example/ReferenceCurves/$producer"

        [ -d "$target_path" ] ||
            fail "$example has no $producer directory under ReferenceCurves."
        compgen -G "$producer_path*.csv" > /dev/null ||
            fail "Anonymizing $example left no curve for its $producer."

        replacements+=("$producer_path|$target_path")
    done
done

for source in "${PRODUCER_CURVES_SOURCE[@]}"; do
    family="${source%%:*}"
    example="${source##*:}"
    producer_path="$curves_path/Model/$example/Producer/"
    target_path="$examples_path/Model/ProducerCurves/$family/Producer"

    [ -d "$target_path" ] || fail "There is no producer curve directory for $family."
    compgen -G "$producer_path*.csv" > /dev/null ||
        fail "Anonymizing $example left no curve for the $family producer curves."

    replacements+=("$producer_path|$target_path")
done

# 4. Replace. Every curve of the directory goes first, so a test that is no longer run leaves
#    none behind; the dictionaries and everything else the directory holds stay.
for replacement in "${replacements[@]}"; do
    producer_path="${replacement%%|*}"
    target_path="${replacement##*|}"

    shipped=$(ls "$target_path"/*.csv 2> /dev/null | wc -l)
    rm -f "${target_path:?}"/*.csv
    cp "$producer_path"*.csv "$target_path/"
    regenerated=$(ls "$target_path"/*.csv | wc -l)

    log_msg "Replaced $regenerated curves in $target_path (it had $shipped)"
    if [ "$regenerated" -lt "$shipped" ]; then
        echo -e "${RED}  Fewer curves than the release ships: a test stopped being run.${NC}" >&2
    fi
done

# 5. The dictionaries of the repository stay, but the event they declare is the one the run
#    used: a stale instant or duration silently misplaces every window computed from it.
for replacement in "${replacements[@]}"; do
    producer_path="${replacement%%|*}"
    target_path="${replacement##*|}"

    python3 - "$producer_path" "$target_path" << 'PYCODE'
import sys
from pathlib import Path

METADATA = ("sim_t_event_start", "fault_duration", "frequency_sampling")

generated_dir, target_dir = (Path(argument) for argument in sys.argv[1:3])
updated = 0
for generated in sorted(generated_dir.glob("*.dict")):
    target = target_dir / generated.name
    if not target.is_file():
        target.write_text(generated.read_text(encoding="utf-8"), encoding="utf-8")
        updated += 1
        continue

    values = {}
    for line in generated.read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition("=")
        if name.strip() in METADATA:
            values[name.strip()] = value.strip()

    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = False
    for index, line in enumerate(lines):
        name, separator, value = line.partition("=")
        if separator and name.strip() in values and value.strip() != values[name.strip()]:
            lines[index] = f"{name.rstrip()} = {values[name.strip()]}\n"
            changed = True
    if changed:
        target.write_text("".join(lines), encoding="utf-8")
        updated += 1

print(f"{updated} dictionaries updated in {target_dir}")
PYCODE
done

log_msg "Done. Review the changes with 'git status' before committing them."
