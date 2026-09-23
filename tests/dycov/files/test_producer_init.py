#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the writing of the initial values into the producer PAR."""

import pytest
from lxml import etree

from dycov.files import par_access, producer_init

_NS = "http://www.rte-france.com/dynawo"


def _make_root(ns=_NS):
    return etree.Element(f"{{{ns}}}root", nsmap={None: ns})


def _add_parset(par_root, par_id, values):
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id=par_id)
    for name, value in values.items():
        etree.SubElement(parset, f"{{{_NS}}}par", name=name, value=value)
    return parset


def test_adjust_load_missing_parset_raises():
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='Aux_Load' was not found"):
        producer_init._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.0)


def test_adjust_load_writes_initial_values():
    par_root = _make_root()
    etree.SubElement(par_root, f"{{{_NS}}}set", id="Aux_Load")

    producer_init._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.2)

    parset = par_root.xpath("//ns:set[@id='Aux_Load']", namespaces={"ns": _NS})[0]
    written = {par.get("name"): float(par.get("value")) for par in parset}
    assert written == {
        "load_P0Pu": 0.1,
        "load_Q0Pu": 0.05,
        "load_U0Pu": 1.0,
        "load_UPhase0": 0.2,
    }


def test_adjust_load_duplicated_parset_raises():
    par_root = _make_root()
    _add_parset(par_root, "Aux_Load", {})
    _add_parset(par_root, "Aux_Load", {})

    with pytest.raises(ValueError, match="Multiple parameter sets with id='Aux_Load' were found"):
        producer_init._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.0)


def test_adjust_load_applied_twice_updates_values_instead_of_duplicating():
    par_root = _make_root()
    etree.SubElement(par_root, f"{{{_NS}}}set", id="Aux_Load")

    producer_init._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.2)
    producer_init._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.3, 0.15, 1.05, 0.4)

    parset = par_root.xpath("//ns:set[@id='Aux_Load']", namespaces={"ns": _NS})[0]
    written = {par.get("name"): float(par.get("value")) for par in parset}
    assert len(parset) == 4
    assert written == {
        "load_P0Pu": 0.3,
        "load_Q0Pu": 0.15,
        "load_U0Pu": 1.05,
        "load_UPhase0": 0.4,
    }


def test_set_parameter_updates_existing_value():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {"generator_P0Pu": "0.5"})

    producer_init._set_parameter([parset], {"ns": _NS}, "generator_P0Pu", -1, 0.75)

    parameter = parset.xpath("ns:par[@name='generator_P0Pu']", namespaces={"ns": _NS})[0]
    assert parameter.get("value") == "-0.75"


def test_set_parameter_creates_parameter_only_when_requested():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {})

    producer_init._set_parameter([parset], {"ns": _NS}, "generator_Q0Pu", 1, 0.25)
    producer_init._set_parameter(
        [parset], {"ns": _NS}, "generator_P0Pu", 1, 0.5, create_if_missing=True
    )

    assert [par.get("name") for par in parset] == ["generator_P0Pu"]
    created = next(par for par in parset if par.get("name") == "generator_P0Pu")
    assert created.get("type") == "DOUBLE"
    assert created.get("value") == "0.5"


def test_set_parameter_without_name_is_noop():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {})

    producer_init._set_parameter([parset], {"ns": _NS}, None, 1, 0.5, create_if_missing=True)

    assert len(parset) == 0


def test_set_parameter_creates_par_in_document_namespace():
    par_root = _make_root()
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id="parGen")

    producer_init._set_parameter(
        [parset], {"ns": _NS}, "generator_P0Pu", 1, 0.5, create_if_missing=True
    )

    created = parset.xpath("ns:par[@name='generator_P0Pu']", namespaces={"ns": _NS})
    assert len(created) == 1
    assert created[0].tag == f"{{{_NS}}}par"
    assert created[0].get("type") == "DOUBLE"
    assert created[0].get("value") == "0.5"


def test_set_parameter_repeated_create_updates_instead_of_duplicating():
    par_root = _make_root()
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id="parGen")

    producer_init._set_parameter(
        [parset], {"ns": _NS}, "generator_P0Pu", 1, 0.5, create_if_missing=True
    )
    producer_init._set_parameter(
        [parset], {"ns": _NS}, "generator_P0Pu", -1, 0.75, create_if_missing=True
    )

    assert len(parset) == 1
    assert parset[0].get("value") == "-0.75"


def test_apply_control_mode_with_valid_parameters(monkeypatch):
    class DummyDynawoTranslator:
        def get_generator_parameters(self, generator, control_mode, zone):
            return ["MwpqMode", "MqG"]

        def is_valid_control_mode(self, generator, generator_control_mode, parameters, zone):
            return True, "USetpoint"

        def get_dynawo_variable(self, lib, name):
            return (1, name)

    monkeypatch.setattr(producer_init, "dynawo_translator", DummyDynawoTranslator())
    monkeypatch.setattr(par_access, "dynawo_translator", DummyDynawoTranslator())

    class DummyGen:
        lib = "IEC"
        id = "Gen1"
        UseVoltageDroop = False
        par_id = "parGen"

    par_root = _make_root()
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id="parGen")
    etree.SubElement(parset, f"{{{_NS}}}par", name="MwpqMode", value="3")
    etree.SubElement(parset, f"{{{_NS}}}par", name="MqG", value="1")

    is_valid, control_mode_name = producer_init._apply_control_mode(
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

    monkeypatch.setattr(producer_init, "dynawo_translator", DummyDynawoTranslator())

    class DummyGen:
        lib = "IEC"
        id = "Gen1"

    parset = etree.SubElement(_make_root(), f"{{{_NS}}}set", id="parGen")

    is_valid, control_mode_name = producer_init._apply_control_mode(
        DummyGen(), [parset], {"ns": _NS}, "USetpoint", 3
    )

    assert is_valid is False
    assert control_mode_name is None


def test_adjust_producer_init_without_group_xfmr(tmp_path, monkeypatch):
    """A generator without a group transformer must still get its init written.

    Regression for the S/ConverterLVControl=False topology: with an empty xfmrs
    list the generator must not be skipped (the transformer step is simply not
    applied).
    """
    from dycov.model.parameters import GenParams, Terminal

    ns = "http://www.rte-france.com/dynawo"
    par_root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    producer_par = tmp_path / "Producer.par"
    etree.ElementTree(par_root).write(
        str(producer_par), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )

    calls = {"gen": 0, "xfmr": 0}

    def fake_adjust_generator(*args, **kwargs):
        calls["gen"] += 1
        return True

    def fake_adjust_transformer(*args, **kwargs):
        calls["xfmr"] += 1

    monkeypatch.setattr(producer_init, "_adjust_generator", fake_adjust_generator)
    monkeypatch.setattr(producer_init, "_adjust_transformer", fake_adjust_transformer)

    gen = GenParams(
        id="Gen1",
        lib="IEC",
        par_id="parGen",
        terminals=(Terminal(connected_equipment=None),),
        s_nom=90,
        i_max=None,
        p=1,
        q=1,
        voltage_droop=None,
        use_voltage_droop=False,
    )

    is_test_applicable = producer_init.adjust_producer_init(
        tmp_path,
        producer_par,
        [gen],
        [],
        None,
        None,
        None,
        "USetpoint",
        False,
        1,
    )

    assert is_test_applicable is True
    assert calls["gen"] == 1
    assert calls["xfmr"] == 0
