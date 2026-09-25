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


class DummyProducer:
    def __init__(self):
        self.zone = None

    def set_zone(self, zone, name):
        self.zone = zone

    def get_sim_type_str(self):
        return "performance"


class DummyParams:
    def __init__(self, producer):
        self._producer = producer

    def get_producer(self):
        return self._producer


class DummyBenchmark:
    instances = []

    def __init__(
        self, pcs_name, pcs_id, pcs_zone, producer_name, report_name, bm_name, parameters, producer
    ):
        self._name = bm_name
        self.generated = False
        DummyBenchmark.instances.append(self)

    def get_name(self):
        return self._name

    def validate(self, summary_list, pcs_results):
        pcs_results[self._name] = "validated"
        return self._name == "BM_OK"

    def get_figures_description(self):
        return {"fig_" + self._name: 1}

    def generate(self):
        self.generated = True


class DummyConfig:
    def __init__(self, config_dir):
        self._config_dir = config_dir
        self.loaded = None

    def get_config_dir(self):
        return self._config_dir

    def get_value(self, section, key):
        return "templates"

    def get_int(self, section, key, default):
        return 1

    def get_list(self, section, key):
        return ["BM"]

    def load_pcs_config(self, pcs_path, user_pcs_path=None, dtr_pcs_path=None):
        self.loaded = (pcs_path, user_pcs_path, dtr_pcs_path)


def _make_pcs(monkeypatch, bms=("BM_OK", "BM_KO")):
    import dycov.model.pcs as pcs_module
    from dycov.configuration.cfg import Config
    from dycov.model.pcs import Pcs

    DummyBenchmark.instances = []
    monkeypatch.setattr(pcs_module, "Benchmark", DummyBenchmark)
    monkeypatch.setattr(Config, "get_value", lambda *a, **k: "templates")
    monkeypatch.setattr(
        Pcs,
        "_Pcs__prepare_pcs_config",
        lambda self, producer: ("Report.tex", list(bms), 7, 2),
    )

    return Pcs("Prod", "PCS_Test", DummyParams(DummyProducer()))


def test_initialize_and_getters(monkeypatch):
    pcs = _make_pcs(monkeypatch)

    assert pcs.get_name() == "PCS_Test"
    assert pcs.get_producer_name() == "Prod"
    assert pcs.get_zone() == 2
    assert isinstance(pcs.get_producer(), DummyProducer)
    assert pcs.get_producer().zone == 2  # set_zone was called with pcs_zone
    assert repr(pcs) == "PCS_Test"
    assert str(pcs) == "PCS_Test"
    assert len(DummyBenchmark.instances) == 2


def test_is_valid(monkeypatch):
    pcs = _make_pcs(monkeypatch)

    # __prepare_pcs_config is mocked, so both flags stay False.
    assert pcs.is_valid() is False

    pcs._has_user_config = True
    assert pcs.is_valid() is True


def test_validate_aggregates_benchmarks(monkeypatch):
    pcs = _make_pcs(monkeypatch, bms=("BM_OK", "BM_KO"))
    summary_list = []

    report_name, success, pcs_results = pcs.validate(summary_list)

    assert report_name == "Report.tex"
    assert success is True  # at least one benchmark (BM_OK) succeeded
    assert pcs_results["id"] == 7
    assert pcs_results["zone"] == 2
    assert pcs_results["producer"] == "Prod"
    assert pcs_results["BM_OK"] == "validated"

    figures = pcs.get_figures_description()
    assert "PCS_Test.BM_OK" in figures
    assert figures["PCS_Test.BM_OK"] == {"fig_BM_OK": 1}


def test_validate_all_fail(monkeypatch):
    pcs = _make_pcs(monkeypatch, bms=("BM_KO",))

    _, success, _ = pcs.validate([])

    assert success is False


def test_generate(monkeypatch):
    pcs = _make_pcs(monkeypatch)

    pcs.generate()

    assert all(bm.generated for bm in DummyBenchmark.instances)


def _prepare_pcs_config(monkeypatch, tmp_path, tool_file, user_file):
    import dycov.model.pcs as pcs_module
    from dycov.model.pcs import Pcs

    DummyBenchmark.instances = []
    dummy_config = DummyConfig(tmp_path / "user_config")
    found = {
        Path(pcs_module.__file__).resolve().parent.parent: tool_file,
        dummy_config.get_config_dir(): user_file,
    }
    monkeypatch.setattr(pcs_module, "Benchmark", DummyBenchmark)
    monkeypatch.setattr(pcs_module, "config", dummy_config)
    monkeypatch.setattr(
        Pcs,
        "_Pcs__get_pcs_path",
        lambda self, producer, source_path: found.get(source_path),
    )

    pcs = Pcs("Prod", "PCS_Test", DummyParams(DummyProducer()))
    return pcs, dummy_config


def test_prepare_pcs_config_loads_both_files_at_once(monkeypatch, tmp_path):
    tool_file = tmp_path / "tool" / "PCSDescription.ini"
    user_file = tmp_path / "user" / "PCSDescription.ini"

    pcs, dummy_config = _prepare_pcs_config(monkeypatch, tmp_path, tool_file, user_file)

    assert dummy_config.loaded == (tool_file, user_file, None)
    assert pcs.is_valid() is True


def test_prepare_pcs_config_loads_only_the_files_that_exist(monkeypatch, tmp_path):
    user_file = tmp_path / "user" / "PCSDescription.ini"

    pcs, dummy_config = _prepare_pcs_config(monkeypatch, tmp_path, None, user_file)

    assert dummy_config.loaded == (None, user_file, None)
    assert pcs._has_pcs_config is False
    assert pcs._has_user_config is True


def test_prepare_pcs_config_without_any_file_is_not_a_valid_pcs(monkeypatch, tmp_path):
    pcs, dummy_config = _prepare_pcs_config(monkeypatch, tmp_path, None, None)

    assert dummy_config.loaded == (None, None, None)
    assert pcs.is_valid() is False


def test_get_pcs_path_prefers_pcs_description(monkeypatch, tmp_path):
    pcs = _make_pcs(monkeypatch)
    producer = DummyProducer()

    # source_path / "templates" / "performance" / "PCS_Test"
    pcs_dir = tmp_path / "templates" / "performance" / "PCS_Test"
    pcs_dir.mkdir(parents=True)
    # The lookup matches the stem "pcsdescription" (no underscore), so the file
    # must be named PCSDescription.ini to be selected over the others.
    (pcs_dir / "PCSDescription.ini").write_text("[x]\n")
    (pcs_dir / "Other.ini").write_text("[x]\n")

    result = pcs._Pcs__get_pcs_path(producer, tmp_path)

    assert result.name == "PCSDescription.ini"


def test_get_pcs_path_does_not_guess_another_ini(monkeypatch, tmp_path):
    pcs = _make_pcs(monkeypatch)
    producer = DummyProducer()

    pcs_dir = tmp_path / "templates" / "performance" / "PCS_Test"
    pcs_dir.mkdir(parents=True)
    (pcs_dir / "Whatever.ini").write_text("[x]\n")

    assert pcs._Pcs__get_pcs_path(producer, tmp_path) is None


def test_get_pcs_path_missing_dir_returns_none(monkeypatch, tmp_path):
    pcs = _make_pcs(monkeypatch)

    assert pcs._Pcs__get_pcs_path(DummyProducer(), tmp_path) is None


def test_get_pcs_path_no_ini_returns_none(monkeypatch, tmp_path):
    pcs = _make_pcs(monkeypatch)

    pcs_dir = tmp_path / "templates" / "performance" / "PCS_Test"
    pcs_dir.mkdir(parents=True)

    assert pcs._Pcs__get_pcs_path(DummyProducer(), tmp_path) is None
