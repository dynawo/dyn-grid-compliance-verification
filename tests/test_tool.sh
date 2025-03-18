#!/bin/bash
#

# For saner programming:
set -o nounset -o noclobber
set -o errexit -o pipefail

# Some useful functions
GREEN="\\033[1;32m"
NC="\\033[0m"
color_msg()
{
    echo -e "$(date '+%Y-%m-%d %H:%M%S'): $1"  # to the log file, no color, timestamped
    echo -e "${GREEN}$1${NC}" >&6              # to the console, in color
}

launch_test() {
   launch_start=$(date +%s)
   declare -a wind_models=()
   declare -a photo_models=()
   declare -a bess_models=()
   if [ "$iec_models" = true ]; then
      color_msg "IEC models"
      wind_models+=("IECA2015" "IECA2020" "IECA2020WithProtections" "IECB2015" "IECB2020" "IECB2020WithProtections")
   fi
   if [ "$wecc_models" = true ]; then
      color_msg "WECC models"
      wind_models+=("WECCA" "WECCB")
      photo_models+=("WECCCurrentSource" "WECCVoltageSourceA" "WECCVoltageSourceB")
      bess_models+=("WECC")
   fi

   # Model validation
   for bess_model in "${bess_models[@]}"
   do
      start=$(date +%s)
      color_msg "dycov validate -l $launcher -m ./examples/Model/BESS/$bess_model/Dynawo ./examples/Model/BESS/$bess_model/ReferenceCurves -o ../Results/Model/BESS/$bess_model"
      dycov validate -l $launcher -m ./examples/Model/BESS/$bess_model/Dynawo ./examples/Model/BESS/$bess_model/ReferenceCurves -o ../Results/Model/BESS/$bess_model --testing
      end=$(date +%s)
      color_msg "Validate: $bess_model Elapsed Time: $(($end-$start)) seconds"
   done

   for photo_model in "${photo_models[@]}"
   do
      start=$(date +%s)
      color_msg "dycov validate -l $launcher -m ./examples/Model/Photovoltaics/$photo_model/Dynawo ./examples/Model/Photovoltaics/$photo_model/ReferenceCurves -o ../Results/Model/Photovoltaics/$photo_model"
      dycov validate -l $launcher -m ./examples/Model/Photovoltaics/$photo_model/Dynawo ./examples/Model/Photovoltaics/$photo_model/ReferenceCurves -o ../Results/Model/Photovoltaics/$photo_model --testing
      end=$(date +%s)
      color_msg "Validate: $photo_model Elapsed Time: $(($end-$start)) seconds"
   done

   for wind_model in "${wind_models[@]}"
   do
      start=$(date +%s)
      color_msg "dycov validate -l $launcher -m ./examples/Model/Wind/$wind_model/Dynawo ./examples/Model/Wind/$wind_model/ReferenceCurves -o ../Results/Model/Wind/$wind_model"
      dycov validate -l $launcher -m ./examples/Model/Wind/$wind_model/Dynawo ./examples/Model/Wind/$wind_model/ReferenceCurves -o ../Results/Model/Wind/$wind_model --testing
      end=$(date +%s)
      color_msg "Validate: $wind_model Elapsed Time: $(($end-$start)) seconds"
   done

   declare -a models=("GeneratorSynchronousFourWindingsTGov1SexsPss2a")
   if [ "$iec_models" = true ]; then
      models+=("IECB2015" "IECB2020")
   fi
   if [ "$wecc_models" = true ]; then
      models+=("WECCB")
   fi
   declare -a topologies=("Single" "SingleAux" "SingleAuxI" "SingleI")

   # performance validation
   for topology in "${topologies[@]}"
   do
      for model in "${models[@]}"
      do
         start=$(date +%s)
         color_msg "dycov performance -l $launcher -m ./examples/Performance/$topology/$model/Dynawo -o ../Results/Performance/$topology/$model"
         dycov performance -l $launcher -m ./examples/Performance/$topology/$model/Dynawo -o ../Results/Performance/$topology/$model --testing
         end=$(date +%s)
         color_msg "Verificate: $topology - $model Elapsed Time: $(($end-$start)) seconds"
      done
   done

   launch_end=$(date +%s)
   color_msg "Total Elapsed Time: $(($launch_end-$launch_start)) seconds"
}

launcher="dynawo.sh"
iec_models=true
wecc_models=true

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
      --help|-h)
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

rm -rf ../Results
mkdir ../Results
DATETIME=$(date '+%Y%m%d_%H%M%S')
LOG=../Results/test_tool_$DATETIME.log

# Set up redirections to the log file
exec 6>&1      # Link file descriptor #6 with stdout. Saves stdout.
exec >"$LOG"   # stdout redirected to the log file
exec 7>&2      # Link file descriptor #7 with stderr. Saves stderr.
exec 2>&1      # stderr redirected to stdout
# Reminder of how to restore stderr and stdout in case you need it elsewhere in the script:
#exec 1>&6 6>&-    # Restore stdout and close fd 6
#exec 2>&7 7>&-    # Restore stderr and close fd 7

launch_test
