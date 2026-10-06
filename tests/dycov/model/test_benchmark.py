#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the Benchmark: its construction, its report figures and its compliance labels."""

from pathlib import Path

import pytest

from dycov.configuration.cfg import Config
from dycov.model import benchmark
from dycov.model.benchmark import (
    Benchmark,
    _compliance_for_missing_curves,
    _compliance_for_simulation_error,
)
from dycov.model.compliance import Compliance
from dycov.model.parameters import CurvesAvailability, SimulationError

_PCS_BENCHMARK = "PCS.Bench"
_INTERNAL_NODE1_FIGURES = {
    "fig_InternalNode1P": [_PCS_BENCHMARK],
    "fig_InternalNode1Q": [_PCS_BENCHMARK],
}


class DummyProducer:
    def __init__(self, gfm: bool = False, zone: int = 1, controls_internal_node2: bool = True):
        self._gfm = gfm
        self._zone = zone
        self._controls_internal_node2 = controls_internal_node2

    def get_sim_type(self):
        return 0

    def is_gfm(self):
        return self._gfm

    def is_dynawo_model(self):
        return False

    def is_user_curves(self):
        return True

    def get_zone(self):
        return self._zone

    def controls_internal_node2(self):
        return self._controls_internal_node2


class DummyParams:
    def __init__(self, producer: DummyProducer):
        self._producer = producer

    def get_working_dir(self):
        return Path("/tmp")

    def get_output_dir(self):
        return Path("/tmp")

    def get_producer(self):
        return self._producer


def _make_benchmark(monkeypatch, producer: DummyProducer, report_curves: dict = None):
    """A benchmark whose configuration enables nothing but the given report figures."""
    report_curves = report_curves or {}
    monkeypatch.setattr(
        Config,
        "get_list",
        lambda self, section, key: report_curves.get(key, []) if section == "ReportCurves" else [],
    )
    monkeypatch.setattr(benchmark.manage_files, "create_dir", lambda path: None)
    return Benchmark(
        pcs_name="PCS",
        pcs_id=1,
        pcs_zone=producer.get_zone(),
        producer_name="Prod",
        report_name="Report",
        benchmark_name="Bench",
        parameters=DummyParams(producer),
        producer=producer,
    )


def _internal_node1_figures(bm: Benchmark) -> list:
    return [
        (figure.name, figure.variables, figure.in_pdf)
        for figure in bm.get_figures_description()
        if figure.name.startswith("fig_InternalNode1")
    ]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_benchmark_keeps_its_name(monkeypatch):
    bm = _make_benchmark(monkeypatch, DummyProducer())

    assert bm.get_name() == "Bench"


def test_benchmark_of_a_gfm_producer_describes_no_figures(monkeypatch):
    bm = _make_benchmark(monkeypatch, DummyProducer(gfm=True), _INTERNAL_NODE1_FIGURES)

    assert bm.get_figures_description() is None


# ---------------------------------------------------------------------------
# Power at InternalNode1
# ---------------------------------------------------------------------------


def test_internal_node1_power_goes_to_the_pdf_when_the_converter_controls_internal_node2(
    monkeypatch,
):
    """#553: with the controlled point at InternalNode2, the power at InternalNode1 is not the
    controlled power, so the PDF draws it besides the HTML."""
    bm = _make_benchmark(
        monkeypatch, DummyProducer(controls_internal_node2=True), _INTERNAL_NODE1_FIGURES
    )

    assert _internal_node1_figures(bm) == [
        ("fig_InternalNode1P", "BusPDR_BUS_ActivePower", True),
        ("fig_InternalNode1Q", "BusPDR_BUS_ReactivePower", True),
    ]


def test_internal_node1_power_stays_out_of_the_pdf_when_the_converter_controls_it(monkeypatch):
    """#553: with the controlled point at InternalNode1, its power repeats the figures of the
    controlled power, so only the HTML draws it."""
    bm = _make_benchmark(
        monkeypatch, DummyProducer(controls_internal_node2=False), _INTERNAL_NODE1_FIGURES
    )

    assert _internal_node1_figures(bm) == [
        ("fig_InternalNode1P", "BusPDR_BUS_ActivePower", False),
        ("fig_InternalNode1Q", "BusPDR_BUS_ReactivePower", False),
    ]


def test_internal_node1_power_is_drawn_in_power_units_of_snom(monkeypatch):
    bm = _make_benchmark(monkeypatch, DummyProducer(), _INTERNAL_NODE1_FIGURES)

    ylabels = [figure.ylabel for figure in bm.get_figures_description()]

    assert ylabels == ["P (pu base Snom)", "Q (pu base Snom)"]


# ---------------------------------------------------------------------------
# Frequency
# ---------------------------------------------------------------------------


def test_frequency_figures_are_drawn_in_hz(monkeypatch):
    report_curves = {"fig_W": [_PCS_BENCHMARK], "fig_WRef": [_PCS_BENCHMARK]}
    bm = _make_benchmark(monkeypatch, DummyProducer(), report_curves)

    drawn = {figure.name: (figure.ylabel, figure.in_hz) for figure in bm.get_figures_description()}

    assert drawn == {"fig_W": (r"$\omega$ (Hz)", True), "fig_WRef": (r"$\omega$ (Hz)", True)}


def test_figures_read_the_voltages_then_the_powers_then_the_currents(monkeypatch):
    """#553: the power at InternalNode1 sits under the controlled power it is checked against,
    and the figure of the currents with the currents it draws, as the PDF lays them out."""
    compared_figures = ("fig_V", "fig_UIt", "fig_P", "fig_Q", "fig_Ip", "fig_Iq", "fig_I")
    report_curves = {name: [_PCS_BENCHMARK] for name in compared_figures}
    bm = _make_benchmark(monkeypatch, DummyProducer(), report_curves | _INTERNAL_NODE1_FIGURES)

    names = [figure.name for figure in bm.get_figures_description()]

    assert names == [
        "fig_V",
        "fig_UIt",
        "fig_P",
        "fig_Q",
        "fig_InternalNode1P",
        "fig_InternalNode1Q",
        "fig_Ip",
        "fig_Iq",
        "fig_I",
    ]


def test_internal_node1_power_is_not_drawn_outside_zone_1(monkeypatch):
    """#553: in Zone 3 the same columns are the compared power, which fig_P and fig_Q draw."""
    bm = _make_benchmark(monkeypatch, DummyProducer(zone=3), _INTERNAL_NODE1_FIGURES)

    assert _internal_node1_figures(bm) == []


def test_internal_node1_power_is_not_drawn_where_the_benchmark_does_not_declare_it(monkeypatch):
    bm = _make_benchmark(monkeypatch, DummyProducer())

    assert _internal_node1_figures(bm) == []


# ---------------------------------------------------------------------------
# Setpoints drawn over the magnitude they drive
# ---------------------------------------------------------------------------

_SETPOINT_FIGURES = {name: [_PCS_BENCHMARK] for name in ("fig_V", "fig_UIt", "fig_P", "fig_Q")}


def _setpoints(bm: Benchmark) -> dict:
    return {figure.name: figure.setpoint for figure in bm.get_figures_description()}


@pytest.mark.parametrize(
    "controls_internal_node2, voltage_figure", [(True, "fig_UIt"), (False, "fig_V")]
)
def test_zone_1_names_the_setpoint_that_drives_what_each_figure_draws(
    monkeypatch, controls_internal_node2, voltage_figure
):
    """#554: the voltage setpoint drives the voltage of the node the converter controls."""
    producer = DummyProducer(controls_internal_node2=controls_internal_node2)
    bm = _make_benchmark(monkeypatch, producer, _SETPOINT_FIGURES)

    expected = {
        "fig_V": None,
        "fig_UIt": None,
        "fig_P": "ActivePowerSetpointPu",
        "fig_Q": "ReactivePowerSetpointPu",
    }
    assert _setpoints(bm) == expected | {voltage_figure: "VoltageSetpointPu"}


def test_zone_3_names_no_setpoint(monkeypatch):
    bm = _make_benchmark(monkeypatch, DummyProducer(zone=3), _SETPOINT_FIGURES)

    assert set(_setpoints(bm).values()) == {None}


# ---------------------------------------------------------------------------
# Compliance labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "availability, expected",
    [
        (CurvesAvailability.NO_PRODUCER, Compliance.WithoutProducerCurves),
        (CurvesAvailability.NO_REFERENCE, Compliance.WithoutReferenceCurves),
        (CurvesAvailability.NONE, Compliance.WithoutCurves),
    ],
)
def test_compliance_for_missing_curves(availability, expected):
    assert _compliance_for_missing_curves(availability) == expected


@pytest.mark.parametrize(
    "error, expected",
    [
        (SimulationError.FAULT_SIMULATION_FAILS, Compliance.FaultSimulationFails),
        (SimulationError.FAULT_DIP_UNACHIEVABLE, Compliance.FaultDipUnachievable),
        (SimulationError.VOLTAGE_CURVE_MISSING, Compliance.VoltageCurveMissing),
    ],
)
def test_compliance_for_simulation_error(error, expected):
    assert _compliance_for_simulation_error(error) == expected
