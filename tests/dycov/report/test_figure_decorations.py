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
from dycov.report.types import CheckBand, FinalValueBand, FrequencyBand


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
# Band of a check
# ---------------------------------------------------------------------------


def test_the_band_of_a_check_is_drawn_where_the_check_put_it(renderer):
    """#694: the voltage of the I2 example changes by 0.00013 pu, and so narrow is its band."""
    results = {"time_5U_band": [1.0445735, 1.0445865]}

    figure_decorations.draw_tolerance_band(
        renderer, CheckBand(source_key="time_5U_band"), 1.04458, results
    )

    assert renderer.marks == [("hline", 1.0445735), ("hline", 1.0445865)]


def test_a_floor_draws_the_side_of_zero_only(renderer):
    results = {"time_10Pfloor_band": [0.7497, None]}

    figure_decorations.draw_tolerance_band(
        renderer, CheckBand(source_key="time_10Pfloor_band"), 0.833, results
    )

    assert renderer.marks == [("hline", 0.7497)]


def test_a_check_that_left_no_band_draws_none(renderer):
    figure_decorations.draw_tolerance_band(renderer, CheckBand(source_key="time_5P_band"), 1.0, {})

    assert renderer.marks == []


def test_a_band_around_the_final_value_is_still_drawn_from_it(renderer):
    figure_decorations.draw_tolerance_band(
        renderer, FinalValueBand(upper=20.0, lower=10.0), 0.5, {}
    )

    assert renderer.marks == [("hline", pytest.approx(0.7)), ("hline", pytest.approx(0.4))]


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


def _freq1_figure(name: str, bounds: str, **figure) -> "figure_decorations.FigureDescription":
    band = FrequencyBand(upper=1.0, lower=1.0, source_key="freq1_frequency", bounds=bounds)
    return figure_decorations.FigureDescription(
        name=name, variables="NetworkFrequencyPu", ylabel="Hz", frequency_bands=[band], **figure
    )


_NETWORK_FIGURE = {"name": "fig_WRef", "bounds": "units", "in_hz": True}
_CONDENSER_FIGURE = {"name": "fig_SyncCondFreq", "bounds": "sync_condenser", "curves_in_hz": True}


@pytest.mark.parametrize(
    "figure, bounded, drawn",
    [
        (_NETWORK_FIGURE, "units", True),
        (_NETWORK_FIGURE, "sync_condenser", False),
        (_CONDENSER_FIGURE, "sync_condenser", True),
        (_CONDENSER_FIGURE, "units", False),
    ],
)
def test_the_band_of_freq_1_goes_on_the_figure_of_the_frequency_it_bounded(
    renderer, figure, bounded, drawn
):
    """#625: freq_1 bounds the frequency of the synchronous condenser when the test models one,
    which differs from the one the units measure at the load step."""
    description = _freq1_figure(**figure)

    figure_decorations.draw_additional_curves(
        renderer, description, [0.0, 1.0], 1.0, {"freq1_frequency": bounded}, 0.9, 1.1
    )

    hlines = sorted(y for kind, y in renderer.marks if kind == "hline")
    assert hlines == ([pytest.approx(49.0), pytest.approx(51.0)] if drawn else [])


# ---------------------------------------------------------------------------
# MXE
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "zone, curve_name, label",
    [
        (1, "WT_GEN_ActivePowerControlledNode", "active_power"),
        (1, "WT_GEN_ReactivePowerControlledNode", "reactive_power"),
        (1, "WT_GEN_ActiveCurrentNode2", "active_current"),
        (1, "WT_GEN_ReactiveCurrentNode2", "reactive_current"),
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
        "WT_GEN_VoltageNode2",  # the voltage at InternalNode2, not the one at InternalNode1
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
        ("WT_GEN_ActivePowerControlledNode", True),
        ("WT_GEN_ActiveCurrentNode2", False),
        ("WT_GEN_ReactivePowerControlledNode", False),
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

    figure_decorations.draw_mxe(renderer, "WT_GEN_ReactivePowerControlledNode", results, 1)

    assert renderer.marks == _MXE_MARKS
