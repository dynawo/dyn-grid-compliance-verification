#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

from pathlib import Path


def test_initialize_validations(monkeypatch):
    from dycov.model.benchmark import Benchmark

    class DummyParams:
        def get_working_dir(self): return Path("/tmp")
        def get_output_dir(self): return Path("/tmp")
        def get_producer(self): return DummyProducer()

    class DummyProducer:
        def get_sim_type(self): return 0
        def is_gfm(self): return False
        def is_dynawo_model(self): return False
        def is_user_curves(self): return True

    from dycov.configuration.cfg import Config

    monkeypatch.setattr(
        Config,
        "get_list",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr("dycov.model.benchmark.manage_files.create_dir", lambda x: None)

    bm = Benchmark(
        pcs_name="PCS",
        pcs_id=1,
        pcs_zone=1,
        producer_name="Prod",
        report_name="Report",
        benchmark_name="Bench",
        parameters=DummyParams(),
        producer=DummyProducer(),
    )

    assert bm.get_name() == "Bench"

def test_compliance_for_missing_curves():
    from dycov.model.benchmark import _compliance_for_missing_curves
    from dycov.model.parameters import CurvesAvailability

    res = _compliance_for_missing_curves(CurvesAvailability.NO_PRODUCER)
    assert res is not None


def test_get_figures_description(monkeypatch):
    from dycov.model.benchmark import Benchmark

    class DummyParams:
        def get_working_dir(self): return Path("/tmp")
        def get_output_dir(self): return Path("/tmp")
        def get_producer(self): return DummyProducer()

    class DummyProducer:
        def get_sim_type(self): return 0
        def is_gfm(self): return True
        s_nom = 100
        def is_dynawo_model(self): return False

    from dycov.configuration.cfg import Config

    monkeypatch.setattr(
        Config,
        "get_list",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr("dycov.model.benchmark.manage_files.create_dir", lambda x: None)

    bm = Benchmark("PCS", 1, 1, "Prod", "Report", "Bench", DummyParams(), DummyProducer())

    res = bm.get_figures_description()

    assert res is None
