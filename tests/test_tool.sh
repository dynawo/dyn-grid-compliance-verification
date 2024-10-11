launcher=$1;

usage() {
   echo -e "Usage: `basename $0` [OPTIONS]\tFull testing
   
   where OPTIONS can be one of the following:
      --launcher (-l)     Dynawo launcher (default: dynawo.sh)
      --input (-i)        Producer model and curves, and reference curves path (default: ./examples)
      --output (-o)       Output path (default: ./Results)
      --topology (-t)     Selected topology (default: SingleAux)
      
   available topologies:
      * Single
      * SingleI
      * SingleAux
      * SingleAuxI
   " 
}

launch_test() {
   rm -rf $results/*

   # SM performance validation
   echo "dgcv performance -l $launcher -m $models/SM/Dynawo/$topology -o $results/SM/model"
   dgcv performance -l $launcher -m $models/SM/Dynawo/$topology -o $results/SM/model
   echo "dgcv performance -l $launcher -c $models/SM/ProducerCurves -o $results/SM/curves"
   dgcv performance -l $launcher -c $models/SM/ProducerCurves -o $results/SM/curves
   echo "dgcv performance -l $launcher -m $models/SM/Dynawo/$topology -c $models/SM/ProducerCurves -o $results/SM/mixed"
   dgcv performance -l $launcher -m $models/SM/Dynawo/$topology -c $models/SM/ProducerCurves -o $results/SM/mixed

   echo "dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/WECC -o $results/PPM/modelwecc"
   dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/WECC -o $results/PPM/modelwecc
   echo "dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/IEC -o $results/PPM/modeliec"
   dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/IEC2020 -o $results/PPM/modeliec
   echo "dgcv performance -l $launcher -c $models/PPM/ProducerCurves -o $results/PPM/curves"
   dgcv performance -l $launcher -c $models/PPM/ProducerCurves -o $results/PPM/curves
   echo "dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/WECC -c $models/PPM/ProducerCurves -o $results/PPM/mixedwecc"
   dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/WECC -c $models/PPM/ProducerCurves -o $results/PPM/mixedwecc
   echo "dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/IEC -c $models/PPM/ProducerCurves -o $results/PPM/mixediec"
   dgcv performance -l $launcher -m $models/PPM/Dynawo/$topology/IEC2020 -c $models/PPM/ProducerCurves -o $results/PPM/mixediec

   # Model validation
   echo "dgcv validate -l $launcher -m $models/Model/Wind/WECC/Dynawo $models/Model/Wind/WECC/ReferenceCurves -o $results/WindWecc/model"
   dgcv validate -l $launcher -m $models/Model/Wind/WECC/Dynawo $models/Model/Wind/WECC/ReferenceCurves -o $results/WindWecc/model
   echo "dgcv validate -l $launcher -c $models/Model/Wind/WECC/ProducerCurves $models/Model/Wind/WECC/ReferenceCurves -o $results/WindWecc/curves"
   dgcv validate -l $launcher -c $models/Model/Wind/WECC/ProducerCurves $models/Model/Wind/WECC/ReferenceCurves -o $results/WindWecc/curves
   echo "dgcv validate -l $launcher -c $models/Model/Wind/WECC/ProducerCurves $models/Model/Wind/IEC2020/ReferenceCurves -o $results/WindWecc/mixed"
   dgcv validate -l $launcher -c $models/Model/Wind/WECC/ProducerCurves $models/Model/Wind/IEC2020/ReferenceCurves -o $results/WindWecc/mixed
   echo "dgcv validate -l $launcher -m $models/Model/Wind/IEC2020/Dynawo $models/Model/Wind/IEC2020/ReferenceCurves -o $results/WindIec2020/model"
   dgcv validate -l $launcher -m $models/Model/Wind/IEC2020/Dynawo $models/Model/Wind/IEC2020/ReferenceCurves -o $results/WindIec2020/model
   echo "dgcv validate -l $launcher -c $models/Model/Wind/IEC2020/ProducerCurves $models/Model/Wind/IEC2020/ReferenceCurves -o $results/WindIec2020/curves"
   dgcv validate -l $launcher -c $models/Model/Wind/IEC2020/ProducerCurves $models/Model/Wind/IEC2020/ReferenceCurves -o $results/WindIec2020/curves
   echo "dgcv validate -l $launcher -c $models/Model/Wind/IEC2020/ProducerCurves $models/Model/Wind/WECC/ReferenceCurves -o $results/WindIec2020/mixed"
   dgcv validate -l $launcher -c $models/Model/Wind/IEC2020/ProducerCurves $models/Model/Wind/WECC/ReferenceCurves -o $results/WindIec2020/mixed
   echo "dgcv validate -l $launcher -m $models/Model/Wind/IEC2015/Dynawo $models/Model/Wind/IEC2015/ReferenceCurves -o $results/WindIec2015/model"
   dgcv validate -l $launcher -m $models/Model/Wind/IEC2015/Dynawo $models/Model/Wind/IEC2015/ReferenceCurves -o $results/WindIec2015/model
   echo "dgcv validate -l $launcher -c $models/Model/Wind/IEC2015/ProducerCurves $models/Model/Wind/IEC2015/ReferenceCurves -o $results/WindIec2015/curves"
   dgcv validate -l $launcher -c $models/Model/Wind/IEC2015/ProducerCurves $models/Model/Wind/IEC2015/ReferenceCurves -o $results/WindIec2015/curves
   echo "dgcv validate -l $launcher -c $models/Model/Wind/IEC2015/ProducerCurves $models/Model/Wind/WECC/ReferenceCurves -o $results/WindIec2015/mixed"
   dgcv validate -l $launcher -c $models/Model/Wind/IEC2015/ProducerCurves $models/Model/Wind/WECC/ReferenceCurves -o $results/WindIec2015/mixed
}

launcher="dynawo.sh"
models="./examples"
topology="SingleAux"
results="./Results"

while (($#)); do
   case "$1" in
      --launcher|-l)
         launcher=$2
         shift 2
         ;;
      --input|-i)
         models=$2
         shift 2
         ;;     
      --output|-o)
         results=$2
         shift 2
         ;;     
      --topology|-t)
         topology=$2
         shift 2
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

launch_test
