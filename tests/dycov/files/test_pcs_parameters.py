#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the reading of the equipment the PCS declares."""

from dycov.files import pcs_parameters
from dycov.model.parameters import LoadInit

_NS = "http://www.rte-france.com/dynawo"


def test_get_grid_load():
    loads = [
        LoadInit(id="l1", lib=None, p0=1, q0=2, u0=None, u_phase0=None),
        LoadInit(id="l2", lib=None, p0=3, q0=4, u0=None, u_phase0=None),
    ]

    res = pcs_parameters.get_grid_load(loads)

    assert res.p == 4
    assert res.q == 6


def test_get_grid_load_empty():
    res = pcs_parameters.get_grid_load([])

    assert res is None
