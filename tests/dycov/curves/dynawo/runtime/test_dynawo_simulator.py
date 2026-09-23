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

from pathlib import Path

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
    f_nom=50.0,
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
