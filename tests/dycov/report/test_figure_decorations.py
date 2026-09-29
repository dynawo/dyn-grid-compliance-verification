#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the figure decoration helpers."""

import pytest

from dycov.configuration.cfg import Config
from dycov.report import figure_decorations
from dycov.report.types import FrequencyBand


def _mxe_results(measurement_type: str) -> dict:
    """The MXE of every window of a magnitude, as the checks leave it in the results."""
    return {
        f"{window}_mxe_{measurement_type}_{field}": value
        for window, time in (("before", 1.0), ("during", 2.0), ("after", 3.0))
        for field, value in (("value", 0.25), ("position", [time, 0.5]))
    }


_MXE_MARKS = [
    ("vline", 1.0),
    ("vline", 2.0),
    ("vline", 3.0),
    ("annotation", "MXE:\nBefore: 0.250\nDuring: 0.250\nAfter: 0.250\n"),
]


# ---------------------------------------------------------------------------
# Frequency band
# ---------------------------------------------------------------------------


def test_draw_frequency_band_reads_f_nom_from_the_dynawo_section(monkeypatch, renderer):
    calls = []

    def get_float(self, section, key, default):
        calls.append((section, key))
        return 100.0 if (section, key) == ("Dynawo", "f_nom") else default

    monkeypatch.setattr(Config, "get_float", get_float)

    ymin, ymax = figure_decorations.draw_frequency_band(
        renderer, FrequencyBand(upper=1.0, lower=1.0), 0.9, 1.1
    )

    assert ("Dynawo", "f_nom") in calls
    assert renderer.marks == [
        ("hline", pytest.approx((100.0 + 1.0) / 100.0)),
        ("hline", pytest.approx((100.0 - 1.0) / 100.0)),
    ]
    assert ymin == pytest.approx(0.9)
    assert ymax == pytest.approx(1.1)


# ---------------------------------------------------------------------------
# MXE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "zone, curve_name, label",
    [
        (1, "WT_GEN_ActivePowerControlledPu", "active_power"),
        (1, "WT_GEN_ReactivePowerControlledPu", "reactive_power"),
        (1, "WT_GEN_ActiveCurrentInjTerminal", "active_current"),
        (1, "WT_GEN_ReactiveCurrentInjTerminal", "reactive_current"),
        (3, "BusPDR_BUS_ActivePower", "active_power"),
    ],
)
def test_draw_mxe_marks_each_magnitude_a_fault_test_checks_on_its_own_curve(
    renderer, zone, curve_name, label
):
    """#553: in Zone 1 the power checked is the one at the controlled point, whose figures
    carried no MXE while that of the voltage went to the voltage at InternalNode2."""
    results = {f"voltage_dips_{label}_check": True, **_mxe_results(label)}

    figure_decorations.draw_mxe(renderer, curve_name, results, zone)

    assert renderer.marks == _MXE_MARKS


def test_draw_mxe_leaves_unmarked_a_magnitude_the_test_does_not_check(renderer):
    """The errors of every compared curve are measured, but only the checked ones are marked,
    as the compliance table shows them."""
    results = {"voltage_dips_active_power_check": True, **_mxe_results("voltage")}

    figure_decorations.draw_mxe(renderer, "BusPDR_BUS_Voltage", results, 1)

    assert renderer.marks == []


@pytest.mark.parametrize(
    "curve_name",
    [
        "BusPDR_BUS_ActivePower",  # drawn in Zone 1, but compared only in Zone 3
        "WT_GEN_VoltageInjTerminal",  # the voltage at InternalNode2, not the one at InternalNode1
    ],
)
def test_draw_mxe_marks_no_curve_the_zone_does_not_compare_under_the_checked_label(
    renderer, curve_name
):
    results = {
        "voltage_dips_active_power_check": True,
        "voltage_dips_voltage_check": True,
        **_mxe_results("active_power"),
        **_mxe_results("voltage"),
    }

    figure_decorations.draw_mxe(renderer, curve_name, results, 1)

    assert renderer.marks == []


@pytest.mark.parametrize(
    "curve_name, marked",
    [
        ("WT_GEN_ActivePowerControlledPu", True),
        ("WT_GEN_ActiveCurrentInjTerminal", False),
        ("WT_GEN_ReactivePowerControlledPu", False),
    ],
)
def test_draw_mxe_marks_the_controlled_magnitude_of_a_setpoint_test(renderer, curve_name, marked):
    """#553: the MXE of a P setpoint step went to the active current at InternalNode2."""
    results = {
        "setpoint_tracking_controlled_magnitude_check": True,
        "setpoint_tracking_controlled_magnitude_label": "active_power",
        **_mxe_results("tc_controlled_magnitude"),
    }

    figure_decorations.draw_mxe(renderer, curve_name, results, 1)

    assert renderer.marks == (_MXE_MARKS if marked else [])


def test_draw_mxe_marks_a_magnitude_a_setpoint_test_also_tracks(renderer):
    results = {
        "setpoint_tracking_controlled_magnitude_check": True,
        "setpoint_tracking_controlled_magnitude_label": "voltage",
        "setpoint_tracking_reactive_power_check": True,
        **_mxe_results("tc_reactive_power"),
    }

    figure_decorations.draw_mxe(renderer, "WT_GEN_ReactivePowerControlledPu", results, 1)

    assert renderer.marks == _MXE_MARKS
