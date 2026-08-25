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
from types import SimpleNamespace

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


def test_get_parset_missing_id_raises():
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        model_parameters._get_parset(par_root, "missing", {"ns": _NS})


def test_adjust_load_missing_parset_raises():
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='Aux_Load' was not found"):
        model_parameters._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.0)


def test_adjust_load_writes_initial_values():
    par_root = _make_root()
    etree.SubElement(par_root, f"{{{_NS}}}set", id="Aux_Load")

    model_parameters._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.2)

    parset = par_root.xpath("//ns:set[@id='Aux_Load']", namespaces={"ns": _NS})[0]
    written = {par.get("name"): float(par.get("value")) for par in parset}
    assert written == {
        "load_P0Pu": 0.1,
        "load_Q0Pu": 0.05,
        "load_U0Pu": 1.0,
        "load_UPhase0": 0.2,
    }


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


def _producer(p_max_pu=0.8, q_max_pu=0.5, q_min_pu=-0.5, s_nom_pu=1.8, u_nom=20.0):
    return SimpleNamespace(
        p_max_pu=p_max_pu,
        q_max_pu=q_max_pu,
        q_min_pu=q_min_pu,
        s_nom_pu=s_nom_pu,
        u_nom=u_nom,
    )


_OPTION_LOCATION = "'pdr_P' in section [PCS.Model] of '/etc/PCSDescription.ini', line 7"


def _config_stub():
    return SimpleNamespace(describe_option=lambda section, key: _OPTION_LOCATION)


def test_unit_characteristics_exposes_power_and_voltage_bases():
    chars = model_parameters.unit_characteristics(_producer(), u_dim=21.0, line_Xpu=0.05)

    assert chars["Pmax"] == pytest.approx(0.8)
    assert chars["Snom"] == pytest.approx(1.8)
    assert chars["Qmax"] == pytest.approx(0.5)
    assert chars["Qmin"] == pytest.approx(-0.5)
    assert chars["Udim"] == pytest.approx(21.0 / 20.0)
    assert chars["Unom"] == pytest.approx(1.0)
    assert chars["line_XPu"] == pytest.approx(0.05)


def test_unit_characteristics_pmax_aliases_track_active_mode():
    chars = model_parameters.unit_characteristics(_producer(p_max_pu=-0.3), u_dim=20.0)

    assert chars["PmaxInjection"] == pytest.approx(-0.3)
    assert chars["PmaxConsumption"] == pytest.approx(-0.3)


def test_resolve_value_definition_numeric():
    chars = model_parameters.unit_characteristics(_producer(), u_dim=20.0)

    assert model_parameters.resolve_value_definition("1.25", chars) == pytest.approx(1.25)
    assert model_parameters.resolve_value_definition("-0.5", chars) == pytest.approx(-0.5)
    assert model_parameters.resolve_value_definition(".75", chars) == pytest.approx(0.75)


def test_resolve_value_definition_named_and_multiplier():
    chars = model_parameters.unit_characteristics(_producer(s_nom_pu=1.8), u_dim=20.0)

    assert model_parameters.resolve_value_definition("Snom", chars) == pytest.approx(1.8)
    assert model_parameters.resolve_value_definition("0.5*Snom", chars) == pytest.approx(0.9)
    assert model_parameters.resolve_value_definition("-Snom", chars) == pytest.approx(-1.8)


def test_resolve_value_definition_applies_final_sign():
    chars = model_parameters.unit_characteristics(_producer(s_nom_pu=1.8), u_dim=20.0)

    value = model_parameters.resolve_value_definition("0.5*Snom", chars, sign=-1)

    assert value == pytest.approx(-0.9)


def test_resolve_value_definition_unknown_name_raises():
    chars = model_parameters.unit_characteristics(_producer(), u_dim=20.0)

    with pytest.raises(ValueError):
        model_parameters.resolve_value_definition("0.5*Foobar", chars)


def test_resolve_value_definition_invalid_forms_raise():
    chars = model_parameters.unit_characteristics(_producer(), u_dim=20.0)

    for invalid in (None, "", "  ", "-", "2*", "*Snom", "2*3", "Snom*2", "Snom+Unom"):
        with pytest.raises(ValueError):
            model_parameters.resolve_value_definition(invalid, chars)


def test_resolve_value_definition_unknown_name_lists_the_available_magnitudes():
    chars = model_parameters.unit_characteristics(_producer(), u_dim=20.0)

    with pytest.raises(ValueError) as error:
        model_parameters.resolve_value_definition("0.5*snom", chars)

    message = str(error.value)
    assert "Unknown magnitude 'snom'" in message
    assert "case-sensitive" in message
    assert "Defined by" not in message
    for magnitude in chars:
        assert magnitude in message


def test_resolve_value_definition_errors_point_to_the_configuration_option(monkeypatch):
    monkeypatch.setattr(model_parameters, "config", _config_stub())
    chars = model_parameters.unit_characteristics(_producer(), u_dim=20.0)

    for invalid in (None, "0.5*Foobar", "Snom*2"):
        with pytest.raises(ValueError) as error:
            model_parameters.resolve_value_definition(
                invalid, chars, origin=("PCS.Model", "pdr_P")
            )

        assert _OPTION_LOCATION in str(error.value)


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


def test_adjust_producer_init_without_stepup(tmp_path, monkeypatch):
    """A generator without a step-up transformer must still get its init written.

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

    monkeypatch.setattr(model_parameters, "_adjust_generator", fake_adjust_generator)
    monkeypatch.setattr(model_parameters, "_adjust_transformer", fake_adjust_transformer)

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

    is_test_applicable = model_parameters.adjust_producer_init(
        tmp_path,
        producer_par,
        [gen],
        [],
        None,
        None,
        "USetpoint",
        False,
        1,
    )

    assert is_test_applicable is True
    assert calls["gen"] == 1
    assert calls["xfmr"] == 0


def test_adjust_load_applied_twice_updates_values_instead_of_duplicating():
    par_root = _make_root()
    etree.SubElement(par_root, f"{{{_NS}}}set", id="Aux_Load")

    model_parameters._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.2)
    model_parameters._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.3, 0.15, 1.05, 0.4)

    parset = par_root.xpath("//ns:set[@id='Aux_Load']", namespaces={"ns": _NS})[0]
    written = {par.get("name"): float(par.get("value")) for par in parset}
    assert len(parset) == 4
    assert written == {
        "load_P0Pu": 0.3,
        "load_Q0Pu": 0.15,
        "load_U0Pu": 1.05,
        "load_UPhase0": 0.4,
    }


def test_set_parameter_creates_par_in_document_namespace():
    par_root = _make_root()
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id="parGen")

    model_parameters._set_parameter(
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

    model_parameters._set_parameter(
        [parset], {"ns": _NS}, "generator_P0Pu", 1, 0.5, create_if_missing=True
    )
    model_parameters._set_parameter(
        [parset], {"ns": _NS}, "generator_P0Pu", -1, 0.75, create_if_missing=True
    )

    assert len(parset) == 1
    assert parset[0].get("value") == "-0.75"
