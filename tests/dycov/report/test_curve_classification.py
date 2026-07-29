#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

from dycov.report.curve_classification import (
    build_curve_label,
    build_figure_title,
    get_curve_style,
    get_equipment_label,
    get_variable_label,
)


def test_get_equipment_label_bus_default_zone():
    assert get_equipment_label("BusPDR_BUS_Voltage") == "PDR Bus"


def test_get_equipment_label_bus_zone3():
    assert get_equipment_label("BusPDR_BUS_Voltage", zone=3) == "PDR Bus"


def test_get_equipment_label_bus_zone1():
    assert get_equipment_label("BusPDR_BUS_Voltage", zone=1) == "InternalNode1"


def test_get_equipment_label_generator_ignores_zone():
    assert get_equipment_label("Wind_Turbine_GEN_IpInjTerminal", zone=1) == "Wind_Turbine"


def test_get_equipment_label_unknown():
    assert get_equipment_label("NetworkFrequencyPu", zone=1) == ""


def test_build_curve_label_zone1_bus():
    label = build_curve_label(
        "BusPDR_BUS_ActivePower", "calculated", show_equipment=True, zone=1
    )

    assert label == "Active Power — InternalNode1 calculated"


def test_build_curve_label_zone3_bus():
    label = build_curve_label(
        "BusPDR_BUS_ActivePower", "reference", show_equipment=True, zone=3
    )

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
        {"variable": "IpInjTerminal", "type": "generator"},
        {"variable": "IqInjTerminal", "type": "generator"},
    ]

    assert build_figure_title(variables, zone=1) == "Ip / Iq — InternalNode2"


def test_build_figure_title_injector_terminal_voltage_zone1():
    variables = [{"variable": "UPuInjTerminal", "type": "generator"}]

    assert build_figure_title(variables, zone=1) == "Voltage — InternalNode2"


def test_build_figure_title_injector_terminal_currents_zone3_keeps_generator():
    variables = [
        {"variable": "IpInjTerminal", "type": "generator"},
        {"variable": "IqInjTerminal", "type": "generator"},
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
