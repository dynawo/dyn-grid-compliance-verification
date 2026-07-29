#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pandas as pd

from dycov.curves import naming


def test_get_bus_label_zone1():
    assert naming.get_bus_label(1) == "InternalNode1"


def test_get_bus_label_other_zones():
    assert naming.get_bus_label(0) == "PDR Bus"
    assert naming.get_bus_label(3) == "PDR Bus"


def test_to_output_name_zone1_bus_curve():
    assert naming.to_output_name("BusPDR_BUS_Voltage", 1) == "InternalNode1_BUS_Voltage"


def test_to_output_name_zone1_non_bus_curve():
    assert naming.to_output_name("Wind_Turbine_GEN_InjectedActiveCurrent", 1) == (
        "Wind_Turbine_GEN_InjectedActiveCurrent"
    )


def test_to_output_name_zone3_bus_curve():
    assert naming.to_output_name("BusPDR_BUS_Voltage", 3) == "BusPDR_BUS_Voltage"


def test_to_internal_name_zone1_bus_curve():
    assert naming.to_internal_name("InternalNode1_BUS_ReactivePower") == (
        "BusPDR_BUS_ReactivePower"
    )


def test_to_internal_name_passthrough():
    assert naming.to_internal_name("BusPDR_BUS_Voltage") == "BusPDR_BUS_Voltage"
    assert naming.to_internal_name("time") == "time"


def test_rename_columns_for_output_zone1():
    curves = pd.DataFrame(
        {
            "time": [0.0, 1.0],
            "BusPDR_BUS_ActivePower": [0.1, 0.2],
            "Wind_Turbine_GEN_MagnitudeControlledByAVRPu": [1.0, 1.0],
        }
    )

    renamed = naming.rename_columns_for_output(curves, 1)

    assert list(renamed.columns) == [
        "time",
        "InternalNode1_BUS_ActivePower",
        "Wind_Turbine_GEN_MagnitudeControlledByAVRPu",
    ]
    assert list(curves.columns)[1] == "BusPDR_BUS_ActivePower"


def test_rename_columns_for_output_zone3_unchanged():
    curves = pd.DataFrame({"time": [0.0], "BusPDR_BUS_ActivePower": [0.1]})

    renamed = naming.rename_columns_for_output(curves, 3)

    assert list(renamed.columns) == ["time", "BusPDR_BUS_ActivePower"]
