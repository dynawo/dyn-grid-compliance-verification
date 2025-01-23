dgcv performance -m examples/SM/Dynawo/SingleAux -o ../Results/SM
dgcv performance -m examples/PPM/Dynawo/SingleAux/WECC -o ../Results/PPM/WindWECC
dgcv performance -m examples/PPM/Dynawo/SingleAux/IEC2015 -o ../Results/PPM/WindIEC2015
dgcv performance -m examples/PPM/Dynawo/SingleAux/IEC2020 -o ../Results/PPM/WindIEC2020
dgcv performance -m examples/Model/Photovoltaics/WECCCurrentSource/Dynawo/Zone3 -o ../Results/PPM/PVCurrentWECC
dgcv performance -m examples/Model/Photovoltaics/WECCVoltageSource/Dynawo/Zone3 -o ../Results/PPM/PVVoltageWECC
dgcv performance -m examples/Model/BESS/WECC/Dynawo/Zone3 -o ../Results/PPM/BESSWECC
dgcv validate examples/Model/Wind/WECC/ReferenceCurves -m examples/Model/Wind/WECC/Dynawo -o ../Results/Model/WindWECC
dgcv validate examples/Model/Wind/IEC2015/ReferenceCurves -m examples/Model/Wind/IEC2015/Dynawo -o ../Results/Model/WindIEC2015
dgcv validate examples/Model/Wind/IEC2020/ReferenceCurves -m examples/Model/Wind/IEC2020/Dynawo -o ../Results/Model/WindIEC2020
dgcv validate examples/Model/Wind/IEC2020WithProtections/ReferenceCurves -m examples/Model/Wind/IEC2020WithProtections/Dynawo -o ../Results/Model/WindIEC2020WithProtections
dgcv validate examples/Model/Photovoltaics/WECCCurrentSource/ReferenceCurves -m examples/Model/Photovoltaics/WECCCurrentSource/Dynawo -o ../Results/Model/PVCurrentWECC
dgcv validate examples/Model/Photovoltaics/WECCVoltageSource/ReferenceCurves -m examples/Model/Photovoltaics/WECCVoltageSource/Dynawo -o ../Results/Model/PVVoltageWECC
dgcv validate examples/Model/BESS/WECC/ReferenceCurves -m examples/Model/BESS/WECC/Dynawo -o ../Results/Model/BESSWECC
