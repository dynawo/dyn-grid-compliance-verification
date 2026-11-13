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
from dycov.gfm.parameters import GFMParameters
from dycov.gfm.producer import GFMProducer

_SECTION = "GFMParametersTest"


class _Producer(GFMProducer):
    def __init__(self, f_nom: float):
        self._f_nom = f_nom


class _Parameters(GFMParameters):
    def __init__(self, f_nom: float):
        self._producer = _Producer(f_nom)
        self._eval_sections = (_SECTION,)


@pytest.fixture
def pcs_base_angular_frequency():
    config._pcs_default_config.read_string(f"[{_SECTION}]\nWb = 314\n")
    yield
    config._pcs_default_config.remove_section(_SECTION)


@pytest.mark.parametrize("f_nom, base_angular_frequency", [(50.0, 314.0), (60.0, 376.8)])
def test_the_base_angular_frequency_follows_the_nominal_frequency(
    pcs_base_angular_frequency, f_nom, base_angular_frequency
):
    parameters = _Parameters(f_nom)

    assert parameters.get_base_angular_frequency() == pytest.approx(base_angular_frequency)
