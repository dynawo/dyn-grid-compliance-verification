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
import pytest

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


@pytest.mark.parametrize(
    "legacy, current",
    [
        ("WT_GEN_VoltageInjTerminal", "WT_GEN_VoltageNode2"),
        ("WT_GEN_ActiveCurrentInjTerminal", "WT_GEN_ActiveCurrentNode2"),
        ("WT_GEN_ReactiveCurrentInjTerminal", "WT_GEN_ReactiveCurrentNode2"),
        ("WT_GEN_ActivePowerControlledPu", "WT_GEN_ActivePowerControlledNode"),
        ("WT_GEN_ReactivePowerControlledPu", "WT_GEN_ReactivePowerControlledNode"),
        ("WT_GEN_VoltageInjTerminal_b", "WT_GEN_VoltageNode2_b"),
    ],
)
def test_from_legacy_name_translates_the_generator_curves_named_before_the_nodes(legacy, current):
    assert naming.from_legacy_name(legacy) == current


def test_from_legacy_name_passthrough():
    assert naming.from_legacy_name("WT_GEN_VoltageNode2") == "WT_GEN_VoltageNode2"
    assert naming.from_legacy_name("WT_GEN_MagnitudeControlledByAVRPu") == (
        "WT_GEN_MagnitudeControlledByAVRPu"
    )
    assert naming.from_legacy_name("VoltageInjTerminal") == "VoltageInjTerminal"
    assert naming.from_legacy_name("time") == "time"


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


def test_get_network_frequency_curve_names_the_frequency_the_first_unit_measures():
    curves = {
        "time": [0.0],
        "G1_GEN_NetworkFrequencyPu": [0.99],
        "G2_GEN_NetworkFrequencyPu": [0.98],
    }

    naming.get_network_frequency_curve(curves)

    assert curves["NetworkFrequencyPu"] == [0.99]


def test_get_network_frequency_curve_keeps_the_network_frequency_the_curves_carry():
    curves = pd.DataFrame(
        {"time": [0.0], "NetworkFrequencyPu": [1.0], "G1_GEN_NetworkFrequencyPu": [0.99]}
    )

    naming.get_network_frequency_curve(curves)

    assert list(curves["NetworkFrequencyPu"]) == [1.0]


def test_get_network_frequency_curve_without_a_frequency_adds_nothing():
    curves = pd.DataFrame({"time": [0.0], "BusPDR_BUS_ActivePower": [0.1]})

    naming.get_network_frequency_curve(curves)

    assert list(curves.columns) == ["time", "BusPDR_BUS_ActivePower"]
