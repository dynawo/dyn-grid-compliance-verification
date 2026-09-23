#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the low-level access to the parameter sets of a PAR file."""

import pytest
from lxml import etree

from dycov.files import par_access

_NS = "http://www.rte-france.com/dynawo"


def _make_root(ns=_NS):
    return etree.Element(f"{{{ns}}}root", nsmap={None: ns})


def _add_parset(par_root, par_id, values):
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id=par_id)
    for name, value in values.items():
        etree.SubElement(parset, f"{{{_NS}}}par", name=name, value=value)
    return parset


def test_get_parset_missing_id_raises():
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        par_access.get_parset(par_root, "missing", {"ns": _NS})


def test_get_parset_duplicated_id_raises():
    par_root = _make_root()
    _add_parset(par_root, "dup", {})
    _add_parset(par_root, "dup", {})

    with pytest.raises(ValueError, match="Multiple parameter sets with id='dup' were found"):
        par_access.get_parset(par_root, "dup", {"ns": _NS})


def test_get_parameter_reads_value_and_sign():
    par_root = _make_root()
    parset = _add_parset(par_root, "parLoad", {"load_U0Pu": "1.02"})

    sign, value = par_access.get_parameter([parset], {"ns": _NS}, "LoadAlphaBeta", "Voltage0")

    assert sign == 1
    assert value == "1.02"


def test_get_parameter_missing_par_returns_none_value():
    par_root = _make_root()
    parset = _add_parset(par_root, "parLoad", {})

    sign, value = par_access.get_parameter([parset], {"ns": _NS}, "LoadAlphaBeta", "Voltage0")

    assert sign == 1
    assert value is None


def test_get_parameter_unknown_variable_returns_none():
    par_root = _make_root()
    parset = _add_parset(par_root, "parLoad", {"load_U0Pu": "1.02"})

    sign, value = par_access.get_parameter(
        [parset], {"ns": _NS}, "LoadAlphaBeta", "NoSuchToolVariable"
    )

    assert sign is None
    assert value is None
