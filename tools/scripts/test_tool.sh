#!/bin/bash
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

# Some useful functions
GREEN="\\033[1;32m"
NC="\\033[0m"

# fd 6 is for console output (log_msg uses this)
# fd 1 is for log output (standard output)
# fd 7 is for original stderr (not used explicitly in log_msg, but good to preserve)

log_msg() {
    echo "$(date '+%Y-%m-%d %H:%M:%S')     | $1"
    echo -e "${GREEN}$1${NC}" > /dev/tty
}
export -f log_msg

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/models.sh"

parallel_run() {
    local -n cmds=$1

    printf '%s\n' "${cmds[@]}" | \
        xargs -P "$max_parallel" -I {} bash -c "{}"
}

usage() {
    echo "This script is used to test the dycov tool."
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -l, --launcher: specify the Dynawo launcher script to use (default: dynawo.sh)"
    echo "  -e, --examples: specify the examples path (default: ./examples)"
    echo "  -o, --output: specify the output path (default: ../Results)"
    echo "  -r, --remove: remove the output path if it exists"
    echo "  --iec: execute only IEC models"
    echo "  --wecc: execute only WECC models"
    echo "  -v, --validate: execute only model validation"
    echo "  -p, --performance: execute only performance verification"
    echo "  -g, --generate: execute only envelope generation (GFM)"
    echo "  -j, --jobs: max parallel processes per phase (default: 4)"
    echo "  --user-config: configuration file for every run (default: the one of the user)"
    echo "  -d, --debug: run with the log level at DEBUG, which also keeps in every test"
    echo "               directory the curves the criteria compare (signal.csv, reference.csv)"
    echo "  -h, --help: display this help"
    echo
    echo "Notes:"
    echo "  • By default the script runs Validation, Performance, and Envelope Generation phases in parallel (max $max_parallel processes per phase)."
    echo "  • At the end of the run, an Overall Result summary is produced from the log:"
    echo "    CSV at:   <output>/test_tool.log.overall_result_counts.csv"
    echo "    PNG at:   <output>/overall_result_counts.png   (if Matplotlib available)"
    echo "    HTML at:  <output>/overall_result_counts.html  (if Plotly available)"
}

# Function to execute a validation command and record time
run_dycov_validate() {
    local launcher=$1
    local model_path=$2
    local reference_path=$3
    local output_path=$4
    local model_name=$5

    # Full command to execute (for logging purposes)
    local command_to_execute="dycov ${DYCOV_DEBUG:+-d} ${DYCOV_USER_CONFIG:+--user-config $DYCOV_USER_CONFIG} validate -l \"$launcher\" -m \"$model_path\" \"$reference_path\" -o \"$output_path\" --testing"
    log_msg "Executing: $command_to_execute"

    start=$(date +%s)
    # Execute the command
    dycov ${DYCOV_DEBUG:+-d} ${DYCOV_USER_CONFIG:+--user-config "$DYCOV_USER_CONFIG"} validate -l "$launcher" -m "$model_path" "$reference_path" -o "$output_path" --testing
    end=$(date +%s)
    log_msg "Validate: $model_name Elapsed Time: $((end - start)) seconds"
}
# Export the function for xargs to use in subshells
export -f run_dycov_validate

# Writes the selected examples, one per line, and nothing else: its output is read as data.
selected_model_examples() {
    declare -a examples=()
    if [ "$iec_models" = true ]; then
        examples+=("${MODEL_EXAMPLES_IEC[@]}")
    fi
    if [ "$wecc_models" = true ]; then
        examples+=("${MODEL_EXAMPLES_WECC[@]}")
    fi
    printf '%s\n' "${examples[@]}"
}

launch_validate() {
    local -a validation_commands=()

    log_msg "INFO: Model validation of: $(selected_model_examples | tr '\n' ' ')"
    while read -r example; do
        local cmd="run_dycov_validate \"$launcher\" \"$examples_path/Model/$example/Dynawo\" \"$examples_path/Model/$example/ReferenceCurves\" \"$results_path/Model/$example\" \"${example##*/}\""
        validation_commands+=("$cmd")
    done < <(selected_model_examples)

    # Execute commands in parallel with xargs, limiting to 4 processes
    log_msg "INFO: Starting parallel Model validation with max $max_parallel processes..."
    parallel_run validation_commands
    log_msg "INFO: All model validation processes completed."
}

launch_model_as_performance() {
    local -a validation_commands=()

    log_msg "INFO: Performance verification with the Model examples: $(selected_model_examples | tr '\n' ' ')"
    while read -r example; do
        local cmd="run_dycov_performance \"$launcher\" \"$examples_path/Model/$example/Dynawo/Zone3\" \"$results_path/Performance/$example\" \"Model\" \"${example##*/}\""
        validation_commands+=("$cmd")
    done < <(selected_model_examples)

    # Execute commands in parallel with xargs, limiting to 4 processes
    log_msg "INFO: Starting parallel performance verification with Model examples with max $max_parallel processes..."
    parallel_run validation_commands
    log_msg "INFO: All performance verification processes completed."
}

# Function to execute a performance command and record time
run_dycov_performance() {
    local launcher=$1
    local model_path=$2
    local output_path=$3
    local topology=$4
    local model_name=$5

    # Full command to execute (for logging purposes)
    local command_to_execute="dycov ${DYCOV_DEBUG:+-d} ${DYCOV_USER_CONFIG:+--user-config $DYCOV_USER_CONFIG} performance -l \"$launcher\" -m \"$model_path\" -o \"$output_path\" --testing"
    log_msg "Executing: $command_to_execute"

    start=$(date +%s)
    # Execute the command
    dycov ${DYCOV_DEBUG:+-d} ${DYCOV_USER_CONFIG:+--user-config "$DYCOV_USER_CONFIG"} performance -l "$launcher" -m "$model_path" -o "$output_path" --testing
    end=$(date +%s)
    log_msg "Verify: $topology - $model_name Elapsed Time: $((end - start)) seconds"
}
# Export the function for xargs to use in subshells
export -f run_dycov_performance

launch_performance() {
    declare -a models=("GeneratorSynchronousFourWindingsTGov1SexsPss2a")
    if [ "$iec_models" = true ]; then
        log_msg "INFO: Including IEC models for Performance validation."
        models+=("IECB2015" "IECB2020")
    fi
    if [ "$wecc_models" = true ]; then
        log_msg "INFO: Including WECC models for Performance validation."
        models+=("WECC4B")
    fi
    declare -a topologies=("Single" "SingleAux" "SingleAuxI" "SingleI")

    local -a performance_commands=()

    # Performance validation
    for topology in "${topologies[@]}"; do
        for model in "${models[@]}"; do
            local cmd="run_dycov_performance \"$launcher\" \"$examples_path/Performance/$topology/$model/Dynawo\" \"$results_path/Performance/$topology/$model\" \"$topology\" \"$model\""
            performance_commands+=("$cmd")
        done
    done

    log_msg "INFO: Starting parallel performance verification with max $max_parallel processes..."
    parallel_run performance_commands
    log_msg "INFO: All performance verification processes completed."
}

# Function to execute a performance command and record time
run_dycov_generate() {
    local model_path=$1
    local output_path=$2
    local model_name=$3

    # Full command to execute (for logging purposes)
    local command_to_execute="dycov generateEnvelopes -i \"$model_path\" -e -o \"$output_path\""
    log_msg "Executing: $command_to_execute"

    start=$(date +%s)
    # Execute the command
    dycov generateEnvelopes -i "$model_path" -e -o "$output_path"
    end=$(date +%s)
    log_msg "Generate: $model_name Elapsed Time: $((end - start)) seconds"
}
# Export the function for xargs to use in subshells
export -f run_dycov_generate

launch_generate() {
    declare -a models=("Overdamped" "Underdamped" "Fusion")

    local -a generate_commands=()

    for model in "${models[@]}"; do
        local cmd="run_dycov_generate \"$examples_path/GFM/$model/Producer.ini\" \"$results_path/Envelopes/$model\" \"$model\""
        generate_commands+=("$cmd")
    done

    log_msg "INFO: Starting parallel envelope generation with max $max_parallel processes..."
    parallel_run generate_commands
    log_msg "INFO: All envelope generation processes completed."
}

summarize_overall_results() {
    local log_file="$1"
    local results_dir="$2"

    local out_csv="${log_file}.overall_result_counts.csv"
    local out_png="${results_dir}/overall_result_counts.png"
    local out_html="${results_dir}/overall_result_counts.html"

    python3 - "$log_file" "$out_csv" "$out_png" "$out_html" << 'PYCODE'
import sys, csv
from collections import Counter

POSSIBLE_RESULTS = [
    "Compliant",
    "Non-compliant",
    "Invalid test",
    "Failed simulation",
    "Undefined validations",
    "Test without curves",
    "Test without reference curves",
    "Test without producer curves",
    "Fault simulation fails",
    "Fault dip unachievable",
    "Simulation time out",
    "Not applicable test",
]

def parse_counts(log_path: str):
    counts = Counter()
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.rstrip()
            if (not line.strip()
                or line.startswith('-')
                or line.startswith('Producer            PCS            Benchmark')
                or line.startswith('Summary Report')):
                continue
            for label in POSSIBLE_RESULTS:
                if line.endswith(label):
                    counts[label] += 1
                    break
    for label in POSSIBLE_RESULTS:
        counts.setdefault(label, 0)
    return counts

def write_csv(counts, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Overall Result", "Count"])
        for label in POSSIBLE_RESULTS:
            w.writerow([label, counts[label]])

def try_plot_png(counts, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        labels = POSSIBLE_RESULTS
        values = [counts[l] for l in labels]
        fig, ax = plt.subplots(figsize=(10,4.5))
        ax.bar(labels, values, color="#1f77b4")
        ax.set_title("Overall Result counts")
        ax.set_ylabel("Count")
        ax.set_xticklabels(labels, rotation=35, ha="right")
        fig.tight_layout()
        plt.savefig(path, dpi=150)
        return True
    except Exception:
        return False

def try_plot_plotly(counts, path):
    try:
        import plotly.graph_objects as go
        labels = POSSIBLE_RESULTS
        values = [counts[l] for l in labels]
        fig = go.Figure(go.Bar(x=labels, y=values))
        fig.update_layout(
            title="Overall Result counts",
            xaxis_title="Overall Result",
            yaxis_title="Count",
            bargap=0.25,
        )
        fig.write_html(path, include_plotlyjs="cdn", auto_open=False)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    log_path, out_csv, out_png, out_html = sys.argv[1:5]
    counts = parse_counts(log_path)
    total = sum(counts.values())

    write_csv(counts, out_csv)

    # Optional plots
    png_ok = try_plot_png(counts, out_png)
    html_ok = try_plot_plotly(counts, out_html)

    # ---- LOG OUTPUT (stdout -> $LOG) ----
    print("Overall Result counts and percentages:")
    print(f"- Total tests: {total}")
    for label in POSSIBLE_RESULTS:
        c = counts[label]
        pct = (c / total * 100.0) if total > 0 else 0.0
        print(f"  • {label}: {c}  ({pct:.2f}%)")
    print(f"CSV: {out_csv}")
    if png_ok:
        print(f"PNG: {out_png}")
    if html_ok:
        print(f"HTML: {out_html}")
PYCODE

    echo -e "${GREEN}INFO: Overall Result summary generated. CSV at: ${out_csv}${NC}" >&6
    if [ -f "$out_html" ]; then
        echo -e "${GREEN}INFO: Interactive HTML chart: ${out_html}${NC}" >&6
    fi
}

launcher="dynawo.sh"
iec_models=true  # by default, add IEC models
wecc_models=true # by default, add WECC models
# Accumulative execution flags: start disabled; we'll enable after parsing
# If user does not specify any (-v/-p/-g), we will enable all three.
validate=false
performance=false
generate=false
any_exec_flag=false
remove=false     # by default, do NOT remove Results path
debug=false      # by default, the log level is the one of the configuration
examples_path="./examples"
results_path="../Results"
max_parallel=4  # default
DYCOV_USER_CONFIG=""  # empty: every run reads the configuration of the user
DYCOV_DEBUG=""  # empty: the tool logs at the level of its configuration
export DYCOV_USER_CONFIG DYCOV_DEBUG

while (($#)); do
    case "$1" in
        --iec)
            wecc_models=false
            shift
            ;;
        --wecc)
            iec_models=false
            shift
            ;;
        -v | --validate)
            validate=true
            any_exec_flag=true
            shift
            ;;
        -p | --performance)
            performance=true
            any_exec_flag=true
            shift
            ;;
        -g | --generate)
            generate=true
            any_exec_flag=true
            shift
            ;;
        -l | --launcher)
            launcher=$2
            shift 2
            ;;
        -e | --examples)
            examples_path=$2
            shift 2
            ;;
        -o | --output)
            results_path=$2
            shift 2
            ;;
        -r | --remove)
            remove=true
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        -j | --jobs)
            max_parallel=$2
            shift 2
            ;;
        --user-config)
            DYCOV_USER_CONFIG=$2
            shift 2
            ;;
        -d | --debug)
            debug=true
            shift
            ;;
        *)
            echo "$1: invalid option."
            usage
            exit 1
            ;;
    esac
done

# If user did not specify any of -v/-p/-g, enable all phases by default
if [ "$any_exec_flag" = false ]; then
    validate=true
    performance=true
    generate=true
fi

if [ "$debug" = true ]; then
    DYCOV_DEBUG="-d"
fi

if [ "$remove" = true ]; then
    rm -rf "$results_path"
fi
mkdir -p "$results_path"

# Save original stdout before redirecting it to a file
# This is crucial for log_msg to continue writing to the console
exec 6>&1 # Link file descriptor #6 with stdout. Saves stdout.

LOG="$results_path/test_tool.log"

# Now redirect stdout and stderr to a file
exec > "$LOG" # stdout redirected to the log file
exec 7>&2     # Link file descriptor #7 with stderr. Saves stderr.
exec 2>&1     # stderr redirected to stdout

launch_start=$(date +%s)
if [ "$validate" = true ]; then
    log_msg "Starting model validation phase..."
    phase_start=$(date +%s)
    launch_validate
    phase_end=$(date +%s)
    log_msg "Validation time: $((phase_end - phase_start)) seconds"
fi
if [ "$performance" = true ]; then
    log_msg "Starting performance verification phase..."
    phase_start=$(date +%s)
    launch_performance
    launch_model_as_performance
    phase_end=$(date +%s)
    log_msg "Performance time: $((phase_end - phase_start)) seconds"
fi
if [ "$generate" = true ]; then
    log_msg "Starting envelope generation phase..."
    phase_start=$(date +%s)
    launch_generate
    phase_end=$(date +%s)
    log_msg "Generation time: $((phase_end - phase_start)) seconds"
fi
launch_end=$(date +%s)
log_msg "Total Elapsed Time: $((launch_end - launch_start)) seconds"

# Build and print Overall Result metrics
summarize_overall_results "$LOG" "$results_path"
