#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The pool of a parallel validation gets the configuration of the run (#678)."""

import pytest

from dycov.configuration.cfg import config
from dycov.logging import worker_initializer
from dycov.validate import validation as validation_module


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


def test_a_parallel_validation_hands_its_workers_the_configuration_of_the_run(monkeypatch):
    monkeypatch.setattr(validation_module.multiprocessing, "Pool", _RecordingPool)
    validation = object.__new__(validation_module.Validation)
    validation._pcs_list = []

    with pytest.raises(_Stop):
        validation._validate(use_parallel=True, num_processes=2)

    assert _RecordingPool.built_with["initializer"] is worker_initializer
    assert _RecordingPool.built_with["initargs"][1] == config.run_layers()
