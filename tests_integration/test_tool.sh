#!/bin/bash
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

# Some useful functions
GREEN="\\033[1;32m"
NC="\\033[0m"

# fd 6 is for console output (color_msg uses this)
# fd 1 is for log output (standard output)
# fd 7 is for original stderr (not used explicitly in color_msg, but good to preserve)

color_msg()
{
    # Ensure this message goes to the log file
    echo -e "$(date '+%Y-%m-%d %H:%M:%S')     | $1"

    # Ensure this message goes to the console (fd 6)
    # Regardless of the main shell's stdout redirection
    echo -e "${GREEN}$1${NC}" >&6
}

usage()
{
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
   echo "  -h, --help: display this help"
}

# Function to execute a validation command and record time
run_dycov_validate() {
    local launcher=$1
    local model_path=$2
    local reference_path=$3
    local output_path=$4
    local model_name=$5

    # Full command to execute (for logging purposes)
    local command_to_execute="dycov validate -l \"$launcher\" -m \"$model_path\" \"$reference_path\" -o \"$output_path\" --testing"

    start=$(date +%s)
    # Execute the command
    dycov validate -l "$launcher" -m "$model_path" "$reference_path" -o "$output_path" --testing
    end=$(date +%s)
    echo "$(date '+%Y-%m-%d %H:%M:%S')     | Validate: $model_name Elapsed Time: $(($end-$start)) seconds"
}
# Export the function for xargs to use in subshells
export -f run_dycov_validate

launch_validate() {
   declare -a wind_models=()
   declare -a photo_models=()
   declare -a bess_models=()
   if [ "$iec_models" = true ]; then
      color_msg "INFO: Including IEC models for validation."
      wind_models+=("IECA2015" "IECA2020" "IECA2020WithProtections" "IECB2015" "IECB2020" "IECB2020WithProtections")
   fi
   if [ "$wecc_models" = true ]; then
      color_msg "INFO: Including WECC models for validation."
      wind_models+=("WECCA" "WECCB" "WECC")
      photo_models+=("WECCCurrentSource" "WECCVoltageSource1" "WECCVoltageSource2")
      bess_models+=("WECC")
   fi

   local -a validation_commands=()

   # Model validation for BESS models
   for bess_model in "${bess_models[@]}"
   do
      local cmd="run_dycov_validate \"$launcher\" \"$examples_path/Model/BESS/$bess_model/Dynawo\" \"$examples_path/Model/BESS/$bess_model/ReferenceCurves\" \"$results_path/Model/BESS/$bess_model\" \"$bess_model\""
      validation_commands+=("$cmd")
   done

   # Model validation for Photovoltaics models
   for photo_model in "${photo_models[@]}"
   do
      local cmd="run_dycov_validate \"$launcher\" \"$examples_path/Model/Photovoltaics/$photo_model/Dynawo\" \"$examples_path/Model/Photovoltaics/$photo_model/ReferenceCurves\" \"$results_path/Model/Photovoltaics/$photo_model\" \"$photo_model\""
      validation_commands+=("$cmd")
   done

   # Model validation for Wind models
   for wind_model in "${wind_models[@]}"
   do
      local cmd="run_dycov_validate \"$launcher\" \"$examples_path/Model/Wind/$wind_model/Dynawo\" \"$examples_path/Model/Wind/$wind_model/ReferenceCurves\" \"$results_path/Model/Wind/$wind_model\" \"$wind_model\""
      validation_commands+=("$cmd")
   done

   # Execute commands in parallel with xargs, limiting to 4 processes
   color_msg "INFO: Starting parallel validation with max 4 processes..."
   printf '%s\n' "${validation_commands[@]}" | xargs -P 4 -I {} bash -c "{}"
   color_msg "INFO: All validation processes completed."
}

# Function to execute a performance command and record time
run_dycov_performance() {
    local launcher=$1
    local model_path=$2
    local output_path=$3
    local topology=$4
    local model_name=$5

    # Full command to execute (for logging purposes)
    local command_to_execute="dycov performance -l \"$launcher\" -m \"$model_path\" -o \"$output_path\" --testing"

    start=$(date +%s)
    # Execute the command
    dycov performance -l "$launcher" -m "$model_path" -o "$output_path" --testing
    end=$(date +%s)
    echo "$(date '+%Y-%m-%d %H:%M:%S')     | Verify: $topology - $model_name Elapsed Time: $(($end-$start)) seconds"
}
# Export the function for xargs to use in subshells
export -f run_dycov_performance

launch_performance() {
   declare -a models=("GeneratorSynchronousFourWindingsTGov1SexsPss2a")
   if [ "$iec_models" = true ]; then
      models+=("IECB2015" "IECB2020")
   fi
   if [ "$wecc_models" = true ]; then
      models+=("WECCB")
   fi
   declare -a topologies=("Single" "SingleAux" "SingleAuxI" "SingleI")

   local -a performance_commands=()

   # Performance validation
   for topology in "${topologies[@]}"
   do
      for model in "${models[@]}"
      do
         local cmd="run_dycov_performance \"$launcher\" \"$examples_path/Performance/$topology/$model/Dynawo\" \"$results_path/Performance/$topology/$model\" \"$topology\" \"$model\""
         performance_commands+=("$cmd")
      done
   done

   color_msg "INFO: Starting parallel performance verification with max 4 processes..."
   printf '%s\n' "${performance_commands[@]}" | xargs -P 4 -I {} bash -c "{}"
   color_msg "INFO: All performance verification processes completed."
}

# Function to execute a performance command and record time
run_dycov_generate() {
    local model_path=$1
    local output_path=$2
    local model_name=$3

    # Full command to execute (for logging purposes)
    local command_to_execute="dycov generateEnvelopes -i \"$model_path\" -e -o \"$output_path\" --testing"

    start=$(date +%s)
    # Execute the command
    dycov generateEnvelopes -i "$model_path" -e -o "$output_path" --testing
    end=$(date +%s)
    echo "$(date '+%Y-%m-%d %H:%M:%S')     | Verify: $model_name Elapsed Time: $(($end-$start)) seconds"
}
# Export the function for xargs to use in subshells
export -f run_dycov_generate

launch_generate() {
   declare -a models=("GFM_Overdamped" "GFM_Underdamped")

   local -a generate_commands=()

   for model in "${models[@]}"
   do
      local cmd="run_dycov_generate \"$examples_path/$model/Producer.ini\" \"$results_path/Envelopes/$model\" \"$model\""
      generate_commands+=("$cmd")
   done

   color_msg "INFO: Starting parallel envelope generation with max 4 processes..."
   printf '%s\n' "${generate_commands[@]}" | xargs -P 4 -I {} bash -c "{}"
   color_msg "INFO: All envelope generation processes completed."
}



summarize_overall_results() {
  local log_file="$1"
  local results_dir="$2"

  local out_csv="${log_file}.overall_result_counts.csv"
  local out_png="${results_dir}/overall_result_counts.png"
  local out_html="${results_dir}/overall_result_counts.html"

  python3 - <<'PYCODE' "$log_file" "$out_csv" "$out_png" "$out_html"
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

  # Mensajes al terminal (fd 6)
  echo -e "${GREEN}INFO: Overall Result summary generated. CSV at: ${out_csv}${NC}" >&6
  if [ -f "$out_html" ]; then
    echo -e "${GREEN}INFO: Interactive HTML chart: ${out_html}${NC}" >&6
  fi
}


launcher="dynawo.sh"
iec_models=true # by default, add IEC models
wecc_models=true # by default, add WECC models
validate=true  # by default, validate the models
performance=true  # by default, verify the performance
generate=true  # by default, generate the envelopes
remove=false # by default, remove Results path
examples_path="./examples"
results_path="../Results"

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
      -v|--validate)
         performance=false
         generate=false
         shift
         ;;
      -p|--performance)
         validate=false
         generate=false
         shift
         ;;
      -g|--generate)
         performance=false
         validate=false
         shift
         ;;
      -l|--launcher)
         launcher=$2
         shift 2
         ;;
      -e|--examples)
         examples_path=$2
         shift 2
         ;;
      -o|--output)
         results_path=$2
         shift 2
         ;;
      -r|--remove)      
	     remove=true
		 shift
		 ;;
      -h|--help)
         usage
         exit 0
         ;;
      *)
         echo "$1: invalid option."
         usage
         exit 1
         ;;  
   esac
done

if [ "$remove" = true ]; then
	rm -rf "$results_path"
fi
mkdir -p "$results_path"

# Save original stdout before redirecting it to a file
# This is crucial for color_msg to continue writing to the console
exec 6>&1      # Link file descriptor #6 with stdout. Saves stdout.

LOG="$results_path/test_tool.log"

# Now redirect stdout and stderr to a file
exec >"$LOG"   # stdout redirected to the log file
exec 7>&2      # Link file descriptor #7 with stderr. Saves stderr.
exec 2>&1      # stderr redirected to stdout

launch_start=$(date +%s)
if [ "$validate" = true ]; then
   color_msg "Starting model validation phase..."
   launch_validate
fi
if [ "$performance" = true ]; then
   color_msg "Starting performance verification phase..."
   launch_performance
fi
if [ "$generate" = true ]; then
   color_msg "Starting envelope generation phase..."
   launch_generate
fi
launch_end=$(date +%s)
color_msg "Total Elapsed Time: $(($launch_end-$launch_start)) seconds"

# Build and print Overall Result metrics
summarize_overall_results "$LOG" "$results_path"
