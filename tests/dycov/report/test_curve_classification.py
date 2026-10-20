#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import pytest

from dycov.report.curve_classification import (
    build_curve_label,
    build_figure_title,
    get_curve_style,
    get_equipment_label,
    get_variable_label,
    is_setpoint,
)


def test_get_equipment_label_bus_default_zone():
    assert get_equipment_label("BusPDR_BUS_Voltage") == "PDR Bus"


def test_get_equipment_label_bus_zone3():
    assert get_equipment_label("BusPDR_BUS_Voltage", zone=3) == "PDR Bus"


def test_get_equipment_label_bus_zone1():
    assert get_equipment_label("BusPDR_BUS_Voltage", zone=1) == "InternalNode1"


def test_get_equipment_label_generator_ignores_zone():
    assert (
        get_equipment_label("Wind_Turbine_GEN_ActiveCurrentInjTerminal", zone=1) == "Wind_Turbine"
    )


def test_get_equipment_label_unknown():
    assert get_equipment_label("NetworkFrequencyPu", zone=1) == ""


def test_build_curve_label_zone1_bus():
    label = build_curve_label("BusPDR_BUS_ActivePower", "calculated", show_equipment=True, zone=1)

    assert label == "Active Power — InternalNode1 calculated"


def test_build_curve_label_zone3_bus():
    label = build_curve_label("BusPDR_BUS_ActivePower", "reference", show_equipment=True, zone=3)

    assert label == "Active Power — PDR Bus reference"


def test_build_curve_label_without_equipment():
    label = build_curve_label("BusPDR_BUS_ActivePower", "calculated", zone=1)

    assert label == "Active Power calculated"


def test_build_figure_title_str_variables_zone1():
    assert build_figure_title("BusPDR_BUS_Voltage", zone=1) == "Voltage — InternalNode1"


def test_build_figure_title_str_variables_default_zone():
    assert build_figure_title("BusPDR_BUS_Voltage") == "Voltage — PDR Bus"


def test_build_figure_title_bus_variables_zone1():
    variables = [{"variable": "Voltage", "type": "bus"}]

    assert build_figure_title(variables, zone=1) == "Voltage — InternalNode1"


def test_build_figure_title_bus_variables_zone3():
    variables = [{"variable": "Voltage", "type": "bus"}]

    assert build_figure_title(variables, zone=3) == "Voltage — PDR Bus"


def test_build_figure_title_generator_variables_ignores_zone():
    variables = [{"variable": "InjectedActiveCurrent", "type": "generator"}]

    title = build_figure_title(variables, zone=1)

    assert title.endswith("— Generator")


def test_build_figure_title_injector_terminal_currents_zone1():
    variables = [
        {"variable": "ActiveCurrentInjTerminal", "type": "generator"},
        {"variable": "ReactiveCurrentInjTerminal", "type": "generator"},
    ]

    assert build_figure_title(variables, zone=1) == "Ip / Iq — InternalNode2"


def test_build_figure_title_injector_terminal_voltage_zone1():
    variables = [{"variable": "VoltageInjTerminal", "type": "generator"}]

    assert build_figure_title(variables, zone=1) == "Voltage — InternalNode2"


def test_build_figure_title_injector_terminal_currents_zone3_keeps_generator():
    variables = [
        {"variable": "ActiveCurrentInjTerminal", "type": "generator"},
        {"variable": "ReactiveCurrentInjTerminal", "type": "generator"},
    ]

    assert build_figure_title(variables, zone=3) == "Ip / Iq — Generator"


def test_build_figure_title_mixed_generator_variables_zone1_keeps_generator():
    variables = [
        {"variable": "MagnitudeControlledByAVRPu", "type": "generator"},
        {"variable": "VoltageSetpointPu", "type": "generator"},
    ]

    title = build_figure_title(variables, zone=1)

    assert title.endswith("— Generator")


def test_get_variable_label_strips_bus_prefix():
    assert get_variable_label("BusPDR_BUS_ActivePower") == "Active Power"


def test_get_curve_style_reference():
    style = get_curve_style("BusPDR_BUS_ActivePower", is_reference=True)

    assert style.color == "#dd8452"
    assert style.style == "-"


@pytest.mark.parametrize(
    "curve_name",
    [
        "WT_GEN_ActivePowerSetpointPu",
        "WT_GEN_ReactivePowerSetpointPu",
        "WT_GEN_VoltageSetpointPu",
    ],
)
def test_every_setpoint_is_one(curve_name):
    assert is_setpoint(curve_name)


@pytest.mark.parametrize(
    "curve_name", ["WT_GEN_ActivePowerControlledPu", "NetworkFrequencyPu", "BusPDR_BUS_Voltage"]
)
def test_a_magnitude_is_not_a_setpoint(curve_name):
    assert not is_setpoint(curve_name)


def test_the_reference_setpoint_is_told_apart_from_the_simulated_one_and_from_its_magnitude():
    """#554: the two setpoints lie on top of each other when all is well, and the one that
    matters is the one that does not."""
    simulated = get_curve_style("WT_GEN_ActivePowerSetpointPu")
    reference = get_curve_style("WT_GEN_ActivePowerSetpointPu", is_reference=True)
    reference_magnitude = get_curve_style("WT_GEN_ActivePowerControlledPu", is_reference=True)

    assert (simulated.color, simulated.style) == ("#8c8c8c", ":")
    assert (reference.color, reference.style) == ("#dd8452", "--")
    assert reference.style != reference_magnitude.style


@pytest.mark.parametrize(
    "curve_name, role, label",
    [
        (
            "WT_GEN_ActivePowerSetpointPu",
            "calculated",
            "Active Power Setpoint — WT calculated",
        ),
        (
            "WT_GEN_ActivePowerSetpointPu",
            "reference",
            "Active Power Setpoint — WT reference",
        ),
        (
            "WT_GEN_ReactivePowerSetpointPu",
            "reference",
            "Reactive Power Setpoint — WT reference",
        ),
    ],
)
def test_build_curve_label_names_a_setpoint_apart_from_the_power_it_drives(
    curve_name, role, label
):
    assert build_curve_label(curve_name, role, show_equipment=True, zone=1) == label


def test_build_figure_title_leaves_the_setpoint_out():
    variables = [
        {"variable": "ActivePowerControlledPu", "type": "generator"},
        {"variable": "ActivePowerSetpointPu", "type": "generator"},
    ]

    assert build_figure_title(variables, zone=1) == "Active Power — Generator"


def test_build_figure_title_keeps_internal_node2_for_the_voltage_drawn_with_its_setpoint():
    variables = [
        {"variable": "VoltageInjTerminal", "type": "generator"},
        {"variable": "VoltageSetpointPu", "type": "generator"},
    ]

    assert build_figure_title(variables, zone=1) == "Voltage — InternalNode2"


@pytest.mark.parametrize(
    "zone, label",
    [(1, "Voltage Setpoint"), (3, "Plant-level voltage regulation Setpoint")],
)
def test_the_voltage_setpoint_is_the_unit_s_own_in_zone_1(zone, label):
    assert get_variable_label("WT_GEN_VoltageSetpointPu", zone) == label
