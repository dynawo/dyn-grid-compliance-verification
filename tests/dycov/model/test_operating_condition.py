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


class DummyProducer:
    pass


class DummyParams:
    def __init__(self, working_dir):
        self._working_dir = working_dir

    def get_working_dir(self):
        return self._working_dir

    def get_producer(self):
        return DummyProducer()


class DummyValidator:
    def __init__(self, results=None, has_validations=True, u_dim=1.0):
        self._results = results if results is not None else {"compliance": True, "curves": {}}
        self._has_validations = has_validations
        self._u_dim = u_dim
        self.initialized = False

    def initialize_validation_params(self, *args, **kwargs):
        self.initialized = True

    def validate(self, *args, **kwargs):
        return dict(self._results)

    def has_validations(self):
        return self._has_validations

    def get_generator_u_dim(self):
        return self._u_dim


def _make_oc(monkeypatch, working_dir):
    from dycov.model.operating_condition import OperatingCondition
    from dycov.configuration.cfg import Config

    monkeypatch.setattr(Config, "get_float", lambda *args, **kwargs: 0.002)

    return OperatingCondition(DummyParams(working_dir), "PCS", "Bench", "OC")


def test_initialize(monkeypatch, tmp_path):
    oc = _make_oc(monkeypatch, tmp_path)

    assert oc.get_name() == "OC"
    assert oc._pcs_name == "PCS"
    assert oc._bm_name == "Bench"
    assert oc._thr_ss_tol == 0.002
    assert oc._working_dir == tmp_path


def test_validate_with_simulated_curves(monkeypatch, tmp_path):
    import dycov.model.operating_condition as oc_module

    # Force a non-DEBUG level so __validate writes the results.json file.
    monkeypatch.setattr(
        oc_module.dycov_logging,
        "get_logger",
        lambda name: logging.getLogger("test-oc-info"),
    )
    logging.getLogger("test-oc-info").setLevel(logging.INFO)

    oc = _make_oc(monkeypatch, tmp_path)
    validator = DummyValidator(u_dim=2.0)

    results = oc.validate(
        validator,
        tmp_path,
        tmp_path,
        {"event": "params"},
        has_simulated_curves=True,
    )

    assert validator.initialized is True
    assert results["compliance"] is True
    assert results["udim"] == 2.0
    assert (tmp_path / "results.json").exists()


def test_validate_without_validations(monkeypatch, tmp_path):
    import dycov.model.operating_condition as oc_module

    # DEBUG level skips writing the results.json file.
    monkeypatch.setattr(
        oc_module.dycov_logging,
        "get_logger",
        lambda name: logging.getLogger("test-oc-debug"),
    )
    logging.getLogger("test-oc-debug").setLevel(logging.DEBUG)

    oc = _make_oc(monkeypatch, tmp_path)
    validator = DummyValidator(has_validations=False)

    results = oc.validate(
        validator,
        tmp_path,
        tmp_path,
        {},
        has_simulated_curves=True,
    )

    assert results["compliance"] is None
    assert not (tmp_path / "results.json").exists()


def test_validate_without_simulated_curves(monkeypatch, tmp_path):
    oc = _make_oc(monkeypatch, tmp_path)
    validator = DummyValidator(u_dim=3.0)

    results = oc.validate(
        validator,
        tmp_path,
        tmp_path,
        {},
        has_simulated_curves=False,
    )

    assert results["compliance"] is False
    assert results["curves"] is None
    assert results["udim"] == 3.0


def test_generate(monkeypatch, tmp_path):
    import dycov.model.operating_condition as oc_module

    calls = {}

    class DummyGridForming:
        def generate(self, working_path, parameters, pcs_name, bm_name, oc_name):
            calls["args"] = (working_path, pcs_name, bm_name, oc_name)

    monkeypatch.setattr(oc_module, "GridForming", DummyGridForming)

    oc = _make_oc(monkeypatch, tmp_path)
    oc.generate(tmp_path)

    assert calls["args"] == (tmp_path, "PCS", "Bench", "OC")
