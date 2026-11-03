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
