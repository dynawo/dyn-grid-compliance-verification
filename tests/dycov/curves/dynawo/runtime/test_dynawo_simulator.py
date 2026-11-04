#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for what a run of Dynawo reports back."""

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


def _run_writing(monkeypatch, tmp_path, completed=True, writes_curves=True):
    """A run of Dynawo that ends as given and writes, or not, its curves file."""
    from dycov.curves.dynawo.runtime import dynawo_simulator
    from dycov.curves.dynawo.runtime._process import ProcessOutcome

    def run_dynawo_process(*args):
        if writes_curves:
            (tmp_path / "outputs" / "curves").mkdir(parents=True)
            (tmp_path / "outputs" / "curves" / "curves.csv").write_text("time;\n0;\n")
        return ProcessOutcome(completed, "job succeeded" if completed else "job failed", 1.0)

    monkeypatch.setattr(dynawo_simulator, "run_dynawo_process", run_dynawo_process)
    return DynawoSimulator().run_base_dynawo(
        "PCS", "BM", "OC", Path("dynawo.sh"), "TSOModel", tmp_path, Path("outputs")
    )


def test_a_run_reports_the_curves_file_dynawo_wrote(monkeypatch, tmp_path):
    result = _run_writing(monkeypatch, tmp_path)

    assert result.succeeded is True
    assert result.curves_file == tmp_path / "outputs" / "curves" / "curves.csv"


def test_a_run_that_wrote_no_curves_reports_none(monkeypatch, tmp_path):
    result = _run_writing(monkeypatch, tmp_path, writes_curves=False)

    assert result.succeeded is True
    assert result.curves_file is None


def test_a_failed_run_still_says_where_dynawo_left_its_curves(monkeypatch, tmp_path):
    """What the curves mean is for whoever reads them; the simulator only reports the run."""
    result = _run_writing(monkeypatch, tmp_path, completed=False)

    assert result.succeeded is False
    assert result.curves_file == tmp_path / "outputs" / "curves" / "curves.csv"


def test_the_baseline_run_passes_on_the_curves_file(simulated):
    curves_file = Path("/work/outputs/curves/curves.csv")

    result = simulated(DynawoResult(True, None, None, curves_file, 1.0))

    assert result.succeeded is True
    assert result.curves_file == curves_file
