#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for what a simulation reports back about a failure."""

import dataclasses
from pathlib import Path

import pandas as pd
import pytest

from dycov.curves.dynawo.runtime.dynawo_simulator import DynawoResult, DynawoSimulator
from dycov.curves.dynawo.runtime.run_types import DynawoRunInputs

MAX_SIM_TIME = 30.0

RUN = DynawoRunInputs(
    pcs_name="PCS",
    launcher_dwo=Path("/dynawo/dynawo.sh"),
    curves_dict={},
    generators=[],
    s_nom=100.0,
    s_nref=100.0,
)


@pytest.fixture
def simulated(monkeypatch):
    def simulate(result):
        monkeypatch.setattr(
            DynawoSimulator,
            "run_base_dynawo",
            lambda self, *args, **kwargs: result,
        )
        return DynawoSimulator.run_base(
            run=RUN,
            output_dir=Path("/results/PCS/BM/OC"),
            working_oc_dir=Path("/work"),
            jobs_output_dir=Path("outputs"),
            bm_name="BM",
            oc_name="OC",
            max_sim_time=MAX_SIM_TIME,
        )

    return simulate


def test_a_failure_names_what_dynawo_reported_and_where_to_read_it(simulated):
    result = simulated(
        DynawoResult(False, "stderr", "network is not connected at t = 0.5", None, 1.0)
    )

    assert result.log == (
        "Simulation Fails: network is not connected at t = 0.5, "
        "logs in /results/PCS/BM/OC/outputs/logs/dynawo.log"
    )


def test_a_failure_dynawo_did_not_log_keeps_what_it_printed(simulated):
    result = simulated(DynawoResult(False, "job failed", None, None, 1.0))

    assert result.log == "job failed"


def test_a_simulation_over_the_limit_does_not_succeed(simulated):
    result = simulated(DynawoResult(True, None, None, None, MAX_SIM_TIME + 1.0))

    assert not result.succeeded


def _run_returning(monkeypatch, tmp_path, curves, zone=0):
    """A run Dynawo reports as succeeded, whose curves are the given ones."""
    from dycov.curves.dynawo.runtime import dynawo_simulator
    from dycov.curves.dynawo.runtime._process import ProcessOutcome

    def run_dynawo_process(*args):
        (tmp_path / "outputs" / "curves").mkdir(parents=True)
        (tmp_path / "outputs" / "curves" / "curves.csv").write_text("time;\n0;\n")
        return ProcessOutcome(True, "job succeeded", 1.0)

    monkeypatch.setattr(dynawo_simulator, "run_dynawo_process", run_dynawo_process)
    monkeypatch.setattr(dynawo_simulator, "create_curves", lambda *args: curves)
    return DynawoSimulator().run_base_dynawo(
        "PCS",
        "BM",
        "OC",
        Path("dynawo.sh"),
        "TSOModel",
        {},
        tmp_path,
        Path("outputs"),
        [],
        1,
        100,
        zone=zone,
    )


def test_a_run_dynawo_ends_well_whose_curves_diverged_has_failed(monkeypatch, tmp_path):
    """#675: Dynawo stops on NaN or inf, not on a voltage of 4.2e6 pu."""
    diverged = pd.DataFrame({"time": [0.0, 1.0], "BusPDR_BUS_Voltage": [1.0, 4.2e6]})

    result = _run_returning(monkeypatch, tmp_path, diverged)

    assert result.succeeded is False
    assert result.log == "Simulation diverged: BusPDR_BUS_Voltage reached 4.2e+06 pu, beyond 10 pu"
    assert result.curves.empty


def test_a_run_whose_curves_stay_within_their_limits_keeps_them(monkeypatch, tmp_path):
    curves = pd.DataFrame({"time": [0.0, 1.0], "BusPDR_BUS_Voltage": [1.0, 0.9]})

    result = _run_returning(monkeypatch, tmp_path, curves)

    assert result.succeeded is True
    assert result.curves is curves


@pytest.mark.parametrize(
    "limits, curve, reached",
    [
        (
            {"divergence_voltage_limit": 0.95, "divergence_power_limit": 50.0},
            "BusPDR_BUS_Voltage",
            "beyond 0.95 pu",
        ),
        (
            {"divergence_voltage_limit": 5.0, "divergence_power_limit": 0.8},
            "BusPDR_BUS_ActivePower",
            "beyond 0.8 pu",
        ),
    ],
    ids=["voltage", "power"],
)
def test_the_limits_of_a_divergence_come_from_the_configuration(
    monkeypatch, tmp_path, limits, curve, reached
):
    from dycov.curves.dynawo.runtime import dynawo_simulator

    config_type = type(dynawo_simulator.config)
    get_float = config_type.get_float
    monkeypatch.setattr(
        config_type,
        "get_float",
        lambda self, section, key, default=None: (
            limits[key] if key in limits else get_float(self, section, key, default)
        ),
    )
    curves = pd.DataFrame({"time": [0.0, 1.0], curve: [0.7, 0.99]})

    result = _run_returning(monkeypatch, tmp_path, curves)

    assert result.succeeded is False
    assert f"{curve} reached 0.99 pu, {reached}" in result.log


def test_a_run_hands_its_zone_to_the_divergence_check(monkeypatch):
    handed = {}

    def run_base_dynawo(self, *args, **kwargs):
        handed.update(kwargs)
        return DynawoResult(True, None, None, None, 1.0)

    monkeypatch.setattr(DynawoSimulator, "run_base_dynawo", run_base_dynawo)

    DynawoSimulator.run_base(
        run=dataclasses.replace(RUN, zone=1),
        output_dir=Path("/results/PCS/BM/OC"),
        working_oc_dir=Path("/work"),
        jobs_output_dir=Path("outputs"),
        bm_name="BM",
        oc_name="OC",
        max_sim_time=MAX_SIM_TIME,
    )

    assert handed["zone"] == 1


def test_a_divergence_in_zone_1_names_the_bus_as_the_outputs_do(monkeypatch, tmp_path):
    """#275: PDR is the real connection point; the Zone 1 outputs call this bus InternalNode1."""
    diverged = pd.DataFrame({"time": [0.0, 1.0], "BusPDR_BUS_Voltage": [1.0, 2.0e3]})

    result = _run_returning(monkeypatch, tmp_path, diverged, zone=1)

    assert result.log == (
        "Simulation diverged: InternalNode1_BUS_Voltage reached 2e+03 pu, beyond 10 pu"
    )
