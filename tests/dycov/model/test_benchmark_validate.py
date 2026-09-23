#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

import logging
from pathlib import Path

import pytest


class DummyProducer:
    def get_sim_type(self):
        return 0

    def is_gfm(self):
        return False

    def is_dynawo_model(self):
        return False

    def is_user_curves(self):
        return True


class DummyParams:
    def get_working_dir(self):
        return Path("/tmp")

    def get_output_dir(self):
        return Path("/tmp")

    def get_producer(self):
        return DummyProducer()


class DummyOperatingCondition:
    def __init__(self, name):
        self._name = name

    def get_name(self):
        return self._name


class DummyCurvesManager:
    def __init__(self, missed_curves=None):
        self._missed_curves = missed_curves or []

    def get_missed_curves(self, curves_name):
        return self._missed_curves

    def get_solver(self):
        return "IDA"

    def get_generators_imax(self):
        return None

    def get_voltage_dip(self):
        return None


class DummyValidator:
    def get_measurement_names(self):
        return []

    def is_defined_imax_reac(self):
        return False


@pytest.fixture
def benchmark(monkeypatch):
    from dycov.configuration.cfg import Config
    from dycov.model.benchmark import Benchmark

    monkeypatch.setattr(Config, "get_list", lambda *args, **kwargs: [])
    monkeypatch.setattr("dycov.model.benchmark.manage_files.create_dir", lambda x: None)

    bm = Benchmark("PCS", 1, 1, "Prod", "Report", "Bench", DummyParams(), DummyProducer())
    bm._oc_list = [DummyOperatingCondition("First"), DummyOperatingCondition("Second")]
    bm._validator = DummyValidator()
    bm._curves_manager = DummyCurvesManager()
    return bm


def _benchmark_lines(caplog):
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "DyCoV.Benchmark" and record.levelno == logging.INFO
    ]


def test_each_operating_condition_says_where_it_starts_and_how_it_ended(
    benchmark, monkeypatch, caplog
):
    from dycov.model.compliance import Compliance

    monkeypatch.setattr(
        benchmark,
        "_Benchmark__validate_operating_condition",
        lambda op_cond: (True, Compliance.NonCompliant, {"summary": Compliance.NonCompliant}),
        raising=False,
    )

    with caplog.at_level(logging.INFO, logger="DyCoV"):
        benchmark.validate([], {})

    lines = _benchmark_lines(caplog)
    assert lines[0] == "Prod PCS.Bench.First: Start (1/2)"
    assert lines[1].endswith("-> Non-compliant")
    assert lines[2] == "Prod PCS.Bench.Second: Start (2/2)"


def test_an_operating_condition_that_raises_still_says_how_it_ended(
    benchmark, monkeypatch, caplog
):
    def always_raises(op_cond):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        benchmark, "_Benchmark__validate_operating_condition", always_raises, raising=False
    )

    with caplog.at_level(logging.INFO, logger="DyCoV"):
        benchmark.validate([], {})

    assert _benchmark_lines(caplog)[1].endswith("-> Invalid test")


def test_an_unexpected_failure_leaves_its_traceback_in_the_log(benchmark, monkeypatch, caplog):
    def always_raises(op_cond):
        raise KeyError("BusPDR_BUS_ActivePower")

    monkeypatch.setattr(
        benchmark, "_Benchmark__validate_operating_condition", always_raises, raising=False
    )

    with caplog.at_level(logging.INFO, logger="DyCoV"):
        benchmark.validate([], {})

    failures = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert failures
    assert failures[0].exc_info is not None
    assert "BusPDR_BUS_ActivePower" in caplog.text


def test_an_operating_condition_that_raises_does_not_stop_the_others(benchmark, monkeypatch):
    from dycov.model.compliance import Compliance

    evaluated = []

    def one_raises(op_cond):
        evaluated.append(op_cond.get_name())
        if op_cond.get_name() == "First":
            raise KeyError("validate")
        return True, Compliance.Compliant, {"summary": Compliance.Compliant}

    monkeypatch.setattr(
        benchmark, "_Benchmark__validate_operating_condition", one_raises, raising=False
    )
    summary_list = []
    pcs_results = {}

    success = benchmark.validate(summary_list, pcs_results)

    assert evaluated == ["First", "Second"]
    assert [entry.compliance for entry in summary_list] == [
        Compliance.InvalidTest,
        Compliance.Compliant,
    ]
    assert len(pcs_results) == 2
    assert success


def test_the_failed_operating_condition_is_reported_as_invalid(benchmark, monkeypatch):
    from dycov.model.compliance import Compliance

    def always_raises(op_cond):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        benchmark, "_Benchmark__validate_operating_condition", always_raises, raising=False
    )
    summary_list = []
    pcs_results = {}

    success = benchmark.validate(summary_list, pcs_results)

    assert not success
    assert all(entry.compliance == Compliance.InvalidTest for entry in summary_list)
    assert all(result["summary"] == Compliance.InvalidTest for result in pcs_results.values())


def test_missing_curves_make_the_summary_invalid(benchmark, monkeypatch):
    from dycov.model.compliance import Compliance
    from dycov.model.parameters import CurvesAvailability, CurvesCheckResult, SimulationResult

    benchmark._curves_manager = DummyCurvesManager(missed_curves=["BusPDR_BUS_Voltage"])
    monkeypatch.setattr(
        benchmark,
        "_Benchmark__get_curves_check_result",
        lambda names, bm_name, oc_name: CurvesCheckResult(
            working_oc_dir=Path("/tmp"),
            jobs_output_dir=Path("/tmp"),
            event_params={},
            simulation_result=SimulationResult(
                appicable=True, success=True, time_exceeds=False, has_simulated_curves=True
            ),
            availability=CurvesAvailability.ALL,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        benchmark,
        "_Benchmark__validate",
        lambda *args, **kwargs: (True, {}, Compliance.Compliant),
        raising=False,
    )

    _, compliance, results = benchmark._Benchmark__validate_operating_condition(
        DummyOperatingCondition("First")
    )

    assert compliance == Compliance.InvalidTest
    assert results["summary"] == Compliance.InvalidTest
    assert results["missed_columns"] == ["BusPDR_BUS_Voltage"]


def test_a_test_without_reference_curves_keeps_saying_so(benchmark, monkeypatch):
    from dycov.model.compliance import Compliance
    from dycov.model.parameters import CurvesAvailability, CurvesCheckResult, SimulationResult

    benchmark._curves_manager = DummyCurvesManager(missed_curves=["BusPDR_BUS_Voltage"])
    monkeypatch.setattr(
        benchmark,
        "_Benchmark__get_curves_check_result",
        lambda names, bm_name, oc_name: CurvesCheckResult(
            working_oc_dir=Path("/tmp"),
            jobs_output_dir=Path("/tmp"),
            event_params={},
            simulation_result=SimulationResult(
                appicable=True, success=True, time_exceeds=False, has_simulated_curves=True
            ),
            availability=CurvesAvailability.NO_REFERENCE,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        benchmark,
        "_Benchmark__validate",
        lambda *args, **kwargs: (True, {}, Compliance.Compliant),
        raising=False,
    )

    _, compliance, results = benchmark._Benchmark__validate_operating_condition(
        DummyOperatingCondition("First")
    )

    # The missing columns are why there is no reference: saying "invalid test" instead would
    # discard the reason the tool already worked out.
    assert compliance == Compliance.WithoutReferenceCurves
    assert results["summary"] == Compliance.WithoutReferenceCurves
