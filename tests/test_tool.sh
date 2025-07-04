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
      wind_models+=("WECCA" "WECCB")
      photo_models+=("WECCCurrentSource" "WECCVoltageSourceA" "WECCVoltageSourceB")
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


launcher="dynawo.sh"
iec_models=true # by default, add IEC models
wecc_models=true # by default, add WECC models
validate=true  # by default, validate the models
performance=true  # by default, verify the performance
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
         shift
         ;;
      -p|--performance)
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

DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG="$results_path/test_tool_$DATETIME.log"

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
launch_end=$(date +%s)
color_msg "Total Elapsed Time: $(($launch_end-$launch_start)) seconds"