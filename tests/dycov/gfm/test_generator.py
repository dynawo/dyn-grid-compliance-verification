#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
# marinjl@aia.es
# omsg@aia.es
# demiguelm@aia.es
#

import pytest


class _DummyParameters:
    def __init__(self, tmp_path):
        self._tmp_path = tmp_path

    def get_working_dir(self):
        return self._tmp_path / "working"

    def get_output_dir(self):
        return self._tmp_path / "Results"


def test_initialize_working_environment_exits_on_existing_output_dir(monkeypatch, tmp_path):
    from dycov.gfm import generator

    monkeypatch.setattr(generator.manage_files, "create_dir", lambda *a, **k: None)
    monkeypatch.setattr(generator.manage_files, "check_output_dir", lambda path: True)
    gfm_generation = object.__new__(generator.GFMGeneration)
    gfm_generation._parameters = _DummyParameters(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        gfm_generation._GFMGeneration__initialize_working_environment()

    assert exc_info.value.code == 1


class _Stop(Exception):
    pass


class _RecordingPool:
    """Pool stand-in that records how it was built and stops the run once it is used."""

    built_with: dict = {}

    def __init__(self, **kwargs):
        _RecordingPool.built_with = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def map(self, function, items):
        raise _Stop


def test_a_parallel_generation_hands_its_workers_the_configuration_of_the_run(
    monkeypatch, tmp_path
):
    """#678: a worker started with forkserver or spawn reads the configuration from the files."""
    from dycov.configuration.cfg import config
    from dycov.gfm import generator
    from dycov.logging import worker_initializer

    monkeypatch.setattr(generator.multiprocessing, "Pool", _RecordingPool)
    gfm_generation = object.__new__(generator.GFMGeneration)
    gfm_generation._parameters = _DummyParameters(tmp_path)
    gfm_generation._pcs_list = []

    with pytest.raises(_Stop):
        gfm_generation.generate(use_parallel=True, num_processes=2)

    assert _RecordingPool.built_with["initializer"] is worker_initializer
    assert _RecordingPool.built_with["initargs"][1] == config.run_layers()


def _generates_all_but(skipped: str):
    """A stand-in of the generation of a PCS that writes one envelope for every PCS but one,
    which only prepares the directory of its operating condition, as an aborted one does."""

    def generate_pcs(pcs_args):
        from dycov.gfm.report import PcsReport

        parameters, pcs_name, producer_name = pcs_args
        oc_dir = parameters.get_working_dir() / producer_name / pcs_name / "Benchmark" / "OC"
        oc_dir.mkdir(parents=True)
        if pcs_name != skipped:
            (oc_dir / "envelopes.csv").write_text("time\n")
        return PcsReport(producer_name, pcs_name, None, [])

    return generate_pcs


def test_a_pcs_that_generates_nothing_is_reported_and_the_others_are_kept(
    monkeypatch, tmp_path, caplog
):
    from dycov.gfm import generator

    monkeypatch.setattr(generator, "_generate_pcs", _generates_all_but("PCS_Invalid"))
    monkeypatch.setattr(generator.report, "create_pdf", lambda pcs_reports, parameters: None)
    gfm_generation = object.__new__(generator.GFMGeneration)
    gfm_generation._parameters = _DummyParameters(tmp_path)
    gfm_generation._pcs_list = [
        (gfm_generation._parameters, pcs_name, "Producer")
        for pcs_name in ("PCS_A", "PCS_Invalid", "PCS_B")
    ]
    (tmp_path / "Results").mkdir()

    gfm_generation.generate(use_parallel=False)

    results = tmp_path / "Results"
    assert sorted(path.name for path in results.iterdir()) == ["PCS_A", "PCS_B"]
    assert (results / "PCS_B" / "Benchmark" / "OC" / "envelopes.csv").exists()
    assert "PCS_Invalid generated no envelopes" in caplog.text
    assert not (tmp_path / "working").exists()
