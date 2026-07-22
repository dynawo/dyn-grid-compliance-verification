#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the producer model parameter extraction helpers."""

import configparser
import math

import pytest
from lxml import etree

from dycov.files import model_parameters
from dycov.model.parameters import LoadInit

_NS = "http://www.rte-france.com/dynawo"


def _make_root(ns=_NS):
    return etree.Element(f"{{{ns}}}root", nsmap={None: ns})


def _write_xml(root, path):
    etree.ElementTree(root).write(
        str(path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )


def test_get_event_times_normal(tmp_path):
    root = _make_root()
    etree.SubElement(root, f"{{{_NS}}}par", name="fault_tBegin", value="1.5")
    etree.SubElement(root, f"{{{_NS}}}par", name="event_tEvent", value="2.5")
    _write_xml(root, tmp_path / "case1.par")

    t1, t2 = model_parameters.get_event_times(tmp_path, "case1", 0.5, 10.0)

    assert t1 == 1.5
    assert t2 == 2.5


def test_get_event_times_missing_values(tmp_path):
    root = _make_root()
    etree.SubElement(root, f"{{{_NS}}}par", name="step_tStep", value="{step}")
    _write_xml(root, tmp_path / "case2.par")

    t1, t2 = model_parameters.get_event_times(tmp_path, "case2", 0.5, 10.0)

    assert math.isnan(t1)
    assert math.isnan(t2)


def test_no_matching_equipment_models(tmp_path):
    dyd_path = tmp_path / "empty.dyd"
    par_path = tmp_path / "empty.par"
    _write_xml(_make_root(), dyd_path)
    _write_xml(_make_root(), par_path)
    ini_file = configparser.ConfigParser()

    result = model_parameters.get_producer_values(dyd_path, par_path, ini_file, s_nref=90.0)

    generators, stepup_xfmrs, aux_load, auxload_xfmr, ppm_xfmr, intline = result
    assert generators == []
    assert stepup_xfmrs == []
    assert aux_load is None
    assert auxload_xfmr is None
    assert ppm_xfmr is None
    assert intline is None


def test_extract_defined_value_with_placeholders():
    assert model_parameters.extract_defined_value("2*b", "b", 0.2) == pytest.approx(0.4)
    assert model_parameters.extract_defined_value("pmax", "pmax", 90) == pytest.approx(90)
    assert model_parameters.extract_defined_value("3*pmax", "pmax", 10) == pytest.approx(30)


def test_extract_defined_value_numeric():
    val = model_parameters.extract_defined_value("2.5", "p", 1)

    assert val == pytest.approx(2.5)


def test_extract_defined_value_errors():
    for invalid in (None, "", "abc", "2*x"):
        with pytest.raises(ValueError):
            model_parameters.extract_defined_value(invalid, "p", 1)


def test_apply_control_mode_with_valid_parameters(monkeypatch):
    class DummyDynawoTranslator:
        def get_generator_parameters(self, generator, control_mode, zone):
            return ["MwpqMode", "MqG"]

        def is_valid_control_mode(self, generator, generator_control_mode, parameters, zone):
            return True, "USetpoint"

        def get_dynawo_variable(self, lib, name):
            return (1, name)

    monkeypatch.setattr(model_parameters, "dynawo_translator", DummyDynawoTranslator())

    class DummyGen:
        lib = "IEC"
        id = "Gen1"
        UseVoltageDroop = False
        par_id = "parGen"

    par_root = _make_root()
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id="parGen")
    etree.SubElement(parset, f"{{{_NS}}}par", name="MwpqMode", value="3")
    etree.SubElement(parset, f"{{{_NS}}}par", name="MqG", value="1")

    is_valid, control_mode_name = model_parameters._apply_control_mode(
        DummyGen(), [parset], {"ns": _NS}, "USetpoint", 3
    )

    assert is_valid is True
    assert control_mode_name == "USetpoint"


def test_apply_control_mode_without_parameters(monkeypatch):
    class DummyDynawoTranslator:
        def get_generator_parameters(self, generator, control_mode, zone):
            return ["MwpqMode"]

        def get_dynawo_variable(self, lib, name):
            return (1, name)

    monkeypatch.setattr(model_parameters, "dynawo_translator", DummyDynawoTranslator())

    class DummyGen:
        lib = "IEC"
        id = "Gen1"

    parset = etree.SubElement(_make_root(), f"{{{_NS}}}set", id="parGen")

    is_valid, control_mode_name = model_parameters._apply_control_mode(
        DummyGen(), [parset], {"ns": _NS}, "USetpoint", 3
    )

    assert is_valid is False
    assert control_mode_name is None


def test_get_grid_load():
    loads = [
        LoadInit(id="l1", lib=None, p0=1, q0=2, u0=None, u_phase0=None),
        LoadInit(id="l2", lib=None, p0=3, q0=4, u0=None, u_phase0=None),
    ]

    res = model_parameters.get_grid_load(loads)

    assert res.p == 4
    assert res.q == 6


def test_get_grid_load_empty():
    res = model_parameters.get_grid_load([])

    assert res is None


def test_find_output_dir(tmp_path):
    root = _make_root()
    etree.SubElement(root, f"{{{_NS}}}outputs", directory="outdir")
    _write_xml(root, tmp_path / "file.jobs")

    res = model_parameters.find_output_dir(tmp_path, "file")

    assert res == "outdir"
