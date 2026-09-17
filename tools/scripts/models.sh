#!/bin/bash
#
# The Model examples that ship with the tool, as <family>/<name> paths under examples/Model.
# Every script that walks them reads the catalogue from here, so adding an example is one edit
# and no script can fall behind another.

MODEL_EXAMPLES_IEC=(
    "Wind/IECA2015"
    "Wind/IECA2020"
    "Wind/IECA2020WithProtections"
    "Wind/IECB2015"
    "Wind/IECB2020"
    "Wind/IECB2020WithProtections"
)

MODEL_EXAMPLES_WECC=(
    "BESS/WECC"
    "Photovoltaics/WECCCurrentSource"
    "Photovoltaics/WECCVoltageSource1"
    "Photovoltaics/WECCVoltageSource2"
    "Photovoltaics/WECCVoltageSource3"
    "Photovoltaics/WECCVoltageSource4"
    "Wind/WECC31"
    "Wind/WECC32"
    "Wind/WECC4"
    "Wind/WECC4A"
    "Wind/WECC4B"
)

# The producer curves of each family are the curves of one of the examples above.
PRODUCER_CURVES_SOURCE=(
    "PPM:Wind/IECB2015"
    "BESS:BESS/WECC"
)
