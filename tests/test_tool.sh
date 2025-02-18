launch_test() {
   rm -rf ../Results

   declare -a models=("GeneratorSynchronousFourWindingsTGov1SexsPss2a" "IECB2015" "IECB2020" "WECCB")
   declare -a topologies=("Single" "SingleAux" "SingleAuxI" "SingleI")

   # performance validation
   for topology in "${topologies[@]}"
   do
      for model in "${models[@]}"
      do
         echo "dgcv performance -l $launcher -m ./examples/Performance/$topology/$model/Dynawo -o ../Results/Performance/$topology/$model"
         dgcv performance -l $launcher -m ./examples/Performance/$topology/$model/Dynawo -o ../Results/Performance/$topology/$model --testing
      done
   done

   declare -a wind_models=("IECA2015" "IECA2020" "IECA2020WithProtections" "WECCA" "IECB2015" "IECB2020" "IECB2020WithProtections" "WECCB")
   declare -a photo_models=("WECCCurrentSource" "WECCVoltageSourceA" "WECCVoltageSourceB")
   declare -a bess_models=("WECC")

   # Model validation
   for bess_model in "${bess_models[@]}"
   do
      echo "dgcv validate -l $launcher -m ./examples/Model/BESS/$bess_model/Dynawo ./examples/Model/BESS/$bess_model/ReferenceCurves -o ../Results/Model/BESS/$bess_model"
      dgcv validate -l $launcher -m ./examples/Model/BESS/$bess_model/Dynawo ./examples/Model/BESS/$bess_model/ReferenceCurves -o ../Results/Model/BESS/$bess_model --testing
   done

   for photo_model in "${photo_models[@]}"
   do
      echo "dgcv validate -l $launcher -m ./examples/Model/Photovoltaics/$photo_model/Dynawo ./examples/Model/Photovoltaics/$photo_model/ReferenceCurves -o ../Results/Model/Photovoltaics/$photo_model"
      dgcv validate -l $launcher -m ./examples/Model/Photovoltaics/$photo_model/Dynawo ./examples/Model/Photovoltaics/$photo_model/ReferenceCurves -o ../Results/Model/Photovoltaics/$photo_model --testing
   done

   for wind_model in "${wind_models[@]}"
   do
      echo "dgcv validate -l $launcher -m ./examples/Model/Wind/$wind_model/Dynawo ./examples/Model/Wind/$wind_model/ReferenceCurves -o ../Results/Model/Wind/$wind_model"
      dgcv validate -l $launcher -m ./examples/Model/Wind/$wind_model/Dynawo ./examples/Model/Wind/$wind_model/ReferenceCurves -o ../Results/Model/Wind/$wind_model --testing
   done

}

launcher="dynawo.sh"

while (($#)); do
   case "$1" in
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

launch_test
