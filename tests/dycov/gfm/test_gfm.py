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

from dycov.configuration.cfg import config
from dycov.gfm.gfm import GridForming
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer

_SECTION = "GFMFigureTest"


class _Producer(GFMProducer):
    def __init__(self, f_nom: float):
        self._f_nom = f_nom


class _Parameters(GFMParameters):
    def __init__(self, f_nom: float):
        self._producer = _Producer(f_nom)
        self._eval_sections = (_SECTION,)


@pytest.fixture
def rocof_test():
    config._pcs_default_config.read_string(f"[{_SECTION}]\nFrequency0 = 49.5\nRoCoF = 0.5\n")
    yield
    config._pcs_default_config.remove_section(_SECTION)


@pytest.mark.parametrize("f_nom", [50.0, 60.0])
def test_figures_show_the_frequencies_of_the_pcs(rocof_test, f_nom):
    lines = GridForming()._get_params_plot_info(
        _Parameters(f_nom), ["Frequency0", "RoCoF"], calculator=None
    )

    assert lines == ["f0 = 49.500 Hz", "RoCoF = 0.500 Hz/s"]
