#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the registry of the curves each zone compares and the ones it only draws."""

import pytest

from dycov.validation import compared_curves

_ZONE_1_COLUMNS = [
    "time",
    "BusPDR_BUS_Voltage",
    "BusPDR_BUS_ActivePower",
    "BusPDR_BUS_ReactivePower",
    "PV_Array_GEN_VoltageInjTerminal",
    "PV_Array_GEN_ActivePowerControlledPu",
    "PV_Array_GEN_ReactivePowerControlledPu",
    "PV_Array_GEN_ActiveCurrentInjTerminal",
    "PV_Array_GEN_ReactiveCurrentInjTerminal",
]
_INTERNAL_NODE1_POWER = ("BusPDR_BUS_ActivePower", "BusPDR_BUS_ReactivePower")


# ---------------------------------------------------------------------------
# Curves a zone only draws
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label, column",
    [
        ("internal_node1_active_power", "BusPDR_BUS_ActivePower"),
        ("internal_node1_reactive_power", "BusPDR_BUS_ReactivePower"),
    ],
)
def test_plot_variables_draws_the_internal_node1_power_in_zone_1(label, column):
    """#553: the power at InternalNode1, where the DTR sets the operating point of a Zone 1
    test, is drawn although the zone compares the power at the controlled point instead."""
    assert compared_curves.plot_variables(1, label) == column


@pytest.mark.parametrize("zone", [0, 3])
@pytest.mark.parametrize("label", ["internal_node1_active_power", "internal_node1_reactive_power"])
def test_plot_variables_draws_no_internal_node1_power_outside_zone_1(zone, label):
    """#553: outside Zone 1 the same columns are the compared power, already drawn as such."""
    assert compared_curves.plot_variables(zone, label) is None


def test_the_curves_zone_1_draws_are_not_required_of_the_reference():
    """#553: a curve the zone only draws is not one the checks ask the reference for, so a
    reference without it has no missing curve."""
    required = [curve.selector for curve in compared_curves.for_zone(1)]

    assert not set(_INTERNAL_NODE1_POWER) & set(required)


def test_the_curves_zone_1_draws_play_no_part_in_the_verdict():
    compared = [column for _, column in compared_curves.resolve_all(1, _ZONE_1_COLUMNS)]

    assert not set(_INTERNAL_NODE1_POWER) & set(compared)


def test_the_curves_zone_1_draws_are_not_asked_of_the_producer():
    names = compared_curves.curve_names(1, ["PV_Array"])

    assert not set(_INTERNAL_NODE1_POWER) & set(names)


@pytest.mark.parametrize("controls_internal_node2", [True, False])
@pytest.mark.parametrize(
    "label, setpoint",
    [
        ("active_power", "ActivePowerSetpointPu"),
        ("reactive_power", "ReactivePowerSetpointPu"),
    ],
)
def test_zone_1_draws_each_power_setpoint_over_the_power_it_drives(
    label, setpoint, controls_internal_node2
):
    """#554: the controlled power is already the one at the point the converter controls."""
    assert compared_curves.setpoint_driving(1, label, controls_internal_node2) == setpoint


@pytest.mark.parametrize(
    "controls_internal_node2, label", [(True, "injector_voltage"), (False, "voltage")]
)
def test_zone_1_draws_the_voltage_setpoint_over_the_voltage_the_converter_controls(
    controls_internal_node2, label
):
    """#554: measured in voltage control, the setpoint lies on the voltage of InternalNode2 when
    the converter controls it, and on the one of InternalNode1 when it does not."""
    assert compared_curves.setpoint_driving(1, label, controls_internal_node2) == (
        "VoltageSetpointPu"
    )


@pytest.mark.parametrize(
    "controls_internal_node2, label", [(True, "voltage"), (False, "injector_voltage")]
)
def test_zone_1_draws_no_setpoint_over_the_voltage_the_converter_does_not_control(
    controls_internal_node2, label
):
    assert compared_curves.setpoint_driving(1, label, controls_internal_node2) is None


@pytest.mark.parametrize(
    "test_type, setpoint",
    [
        ("PSetpoint", "ActivePowerSetpointPu"),
        ("QSetpoint", "ReactivePowerSetpointPu"),
        ("USetpoint", "VoltageSetpointPu"),
    ],
)
def test_a_setpoint_step_steps_the_setpoint_of_its_type(test_type, setpoint):
    assert compared_curves.setpoint_stepped_by(1, test_type) == setpoint


@pytest.mark.parametrize("test_type", ["Others", None])
def test_a_test_that_steps_no_setpoint_of_the_unit_steps_none(test_type):
    """#554: a grid voltage step moves the voltage of the grid, not the setpoint of the unit."""
    assert compared_curves.setpoint_stepped_by(1, test_type) is None


def test_zone_1_asks_the_producer_for_the_power_setpoints_only():
    """#554: the workbook of the TSO asks for no voltage setpoint in Zone 1, and the curves of
    a producer name their generating units by theirs."""
    assert compared_curves.asked_setpoints(1) == (
        "ActivePowerSetpointPu",
        "ReactivePowerSetpointPu",
    )


@pytest.mark.parametrize("zone", [0, 3])
def test_no_setpoint_is_drawn_outside_zone_1(zone):
    assert compared_curves.asked_setpoints(zone) == ()
    assert compared_curves.setpoint_driving(zone, "active_power", True) is None
    assert compared_curves.setpoint_stepped_by(zone, "PSetpoint") is None


def test_the_setpoints_zone_1_draws_play_no_part_in_the_verdict():
    columns = _ZONE_1_COLUMNS + ["PV_Array_GEN_ActivePowerSetpointPu"]

    compared = [column for _, column in compared_curves.resolve_all(1, columns)]

    assert "PV_Array_GEN_ActivePowerSetpointPu" not in compared


# ---------------------------------------------------------------------------
# Curves a zone compares
# ---------------------------------------------------------------------------


def test_plot_variables_names_a_curve_of_the_generating_unit_by_its_suffix():
    variables = compared_curves.plot_variables(1, "active_power")

    assert variables == [{"type": "generator", "variable": "ActivePowerControlledPu"}]


def test_plot_variables_names_a_curve_of_the_bus_in_full():
    assert compared_curves.plot_variables(3, "active_power") == "BusPDR_BUS_ActivePower"


def test_plot_variables_of_an_unknown_label_is_none():
    assert compared_curves.plot_variables(1, "frequency") is None


def test_for_zone_falls_back_to_zone_3_for_a_zone_without_its_own_set():
    assert compared_curves.for_zone(0) == compared_curves.for_zone(3)


def test_resolve_pairs_each_compared_curve_with_its_column():
    resolved = compared_curves.resolve(1, _ZONE_1_COLUMNS)

    assert [(curve.label, column) for curve, column in resolved] == [
        ("voltage", "BusPDR_BUS_Voltage"),
        ("injector_voltage", "PV_Array_GEN_VoltageInjTerminal"),
        ("active_power", "PV_Array_GEN_ActivePowerControlledPu"),
        ("reactive_power", "PV_Array_GEN_ReactivePowerControlledPu"),
        ("active_current", "PV_Array_GEN_ActiveCurrentInjTerminal"),
        ("reactive_current", "PV_Array_GEN_ReactiveCurrentInjTerminal"),
    ]


def test_resolve_all_pairs_a_curve_no_column_carries_with_its_selector():
    resolved = compared_curves.resolve_all(3, ["time", "BusPDR_BUS_Voltage"])

    assert [column for _, column in resolved] == [
        "BusPDR_BUS_Voltage",
        "BusPDR_BUS_ActivePower",
        "BusPDR_BUS_ReactivePower",
        "BusPDR_BUS_ActiveCurrent",
        "BusPDR_BUS_ReactiveCurrent",
        "NetworkFrequencyPu",
    ]


@pytest.mark.parametrize(
    "zone, column, label",
    [
        (1, "PV_Array_GEN_ActivePowerControlledPu", "active_power"),
        (1, "PV_Array_GEN_VoltageInjTerminal", "injector_voltage"),
        (1, "BusPDR_BUS_ActivePower", None),
        (3, "BusPDR_BUS_ActivePower", "active_power"),
    ],
)
def test_in_column_is_the_curve_the_zone_compares_in_a_column(zone, column, label):
    curve = compared_curves.in_column(zone, column)

    assert (curve.label if curve else None) == label


@pytest.mark.parametrize(
    "setpoint, label",
    [
        ("ActivePowerSetpointPu", "active_power"),
        ("VoltageSetpointPu", "voltage"),
        ("UnknownSetpointPu", "reactive_power"),
    ],
)
def test_setpoint_label_is_the_magnitude_the_setpoint_drives(setpoint, label):
    assert compared_curves.setpoint_label(setpoint) == label


def test_column_of_a_label_the_zone_does_not_compare_is_none():
    assert compared_curves.column_of(1, "frequency", _ZONE_1_COLUMNS) is None


def test_column_of_a_curve_no_column_carries_is_none():
    assert compared_curves.column_of(3, "frequency", _ZONE_1_COLUMNS) is None


@pytest.mark.parametrize(
    "setpoint, expected",
    [
        ("ActivePowerSetpointPu", "PV_Array_GEN_ActivePowerControlledPu"),
        ("ReactivePowerSetpointPu", "PV_Array_GEN_ReactivePowerControlledPu"),
        ("VoltageSetpointPu", "BusPDR_BUS_Voltage"),
        ("UnknownSetpointPu", "PV_Array_GEN_ReactivePowerControlledPu"),
    ],
)
def test_for_setpoint_tracks_the_magnitude_the_setpoint_drives(setpoint, expected):
    assert compared_curves.for_setpoint(1, setpoint, _ZONE_1_COLUMNS) == expected


def test_for_setpoint_of_a_magnitude_the_zone_does_not_compare_is_the_setpoint_itself():
    tracked = compared_curves.for_setpoint(1, "NetworkFrequencyPu", _ZONE_1_COLUMNS)

    assert tracked == "NetworkFrequencyPu"


def test_for_setpoint_without_the_column_is_the_selector_so_it_is_reported_missing():
    tracked = compared_curves.for_setpoint(1, "ActivePowerSetpointPu", ["time"])

    assert tracked == "_GEN_ActivePowerControlledPu"


@pytest.mark.parametrize(
    "selector, column, expected",
    [
        ("_GEN_ActivePowerControlledPu", "PV_Array_GEN_ActivePowerControlledPu", True),
        ("_GEN_ActivePowerControlledPu", "PV_Array_GEN_ReactivePowerControlledPu", False),
        ("BusPDR_BUS_Voltage", "BusPDR_BUS_Voltage", True),
        ("BusPDR_BUS_Voltage", "InternalNode1_BUS_Voltage", False),
    ],
)
def test_matches_column(selector, column, expected):
    assert compared_curves.matches_column(selector, column) is expected


def test_curve_names_names_the_curves_of_every_generating_unit():
    names = compared_curves.curve_names(1, ["WT1", "WT2"])

    assert names[:3] == [
        "BusPDR_BUS_Voltage",
        "WT1_GEN_VoltageInjTerminal",
        "WT2_GEN_VoltageInjTerminal",
    ]


@pytest.mark.parametrize(
    "column, expected",
    [
        ("PV_Array_GEN_ActiveCurrentInjTerminal", "Ip"),
        ("BusPDR_BUS_ReactivePower", "Q"),
        ("BusPDR_BUS_Voltage", None),
        ("PV_Array_GEN_InternalAngle", None),
    ],
)
def test_threshold_of(column, expected):
    assert compared_curves.threshold_of(column) == expected
