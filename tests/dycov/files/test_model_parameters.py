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


def _add_parset(par_root, par_id, values):
    parset = etree.SubElement(par_root, f"{{{_NS}}}set", id=par_id)
    for name, value in values.items():
        etree.SubElement(parset, f"{{{_NS}}}par", name=name, value=value)
    return parset


def _add_bbmodel(dyd_root, model_id, lib, par_id):
    return etree.SubElement(
        dyd_root, f"{{{_NS}}}blackBoxModel", id=model_id, lib=lib, parId=par_id
    )


def _add_connect(dyd_root, id1, var1, id2, var2):
    etree.SubElement(dyd_root, f"{{{_NS}}}connect", id1=id1, var1=var1, id2=id2, var2=var2)


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

    generators, group_xfmrs, aux_load, auxload_xfmr, main_xfmr, intline = result
    assert generators == []
    assert group_xfmrs == []
    assert aux_load is None
    assert auxload_xfmr is None
    assert main_xfmr is None
    assert intline is None


def test_get_parset_missing_id_raises():
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        model_parameters._get_parset(par_root, "missing", {"ns": _NS})


def test_get_parset_duplicated_id_raises():
    par_root = _make_root()
    _add_parset(par_root, "dup", {})
    _add_parset(par_root, "dup", {})

    with pytest.raises(ValueError, match="Multiple parameter sets with id='dup' were found"):
        model_parameters._get_parset(par_root, "dup", {"ns": _NS})


def test_get_line_values_missing_parset_raises():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "IntNetwork_Line", "Line", "missing")
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        model_parameters._get_line_values(dyd_root, par_root, None, None)


def test_get_line_values_reads_parameters():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "IntNetwork_Line", "Line", "parLine")
    _add_connect(dyd_root, "IntNetwork_Line", "line_terminal1", "BusPDR", "bus_terminal")
    _add_connect(dyd_root, "IntNetwork_Line", "line_terminal2", "StepUp_Xfmr", "term1")
    par_root = _make_root()
    _add_parset(
        par_root,
        "parLine",
        {"line_RPu": "0.01", "line_XPu": "0.1", "line_BPu": "0.02", "line_GPu": "0.005"},
    )

    lines = model_parameters._get_line_values(dyd_root, par_root, None, None)

    assert len(lines) == 1
    line = lines[0]
    assert line.id == "IntNetwork_Line"
    assert line.lib == "Line"
    assert line.par_id == "parLine"
    assert line.r == pytest.approx(0.01)
    assert line.x == pytest.approx(0.1)
    assert line.b == pytest.approx(0.02)
    assert line.g == pytest.approx(0.005)
    assert line.terminals[0].connected_equipment == "BusPDR"
    assert line.terminals[1].connected_equipment == "StepUp_Xfmr"


def test_get_line_values_applies_provided_impedances():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "IntNetwork_Line", "Line", "parLine")
    par_root = _make_root()
    _add_parset(
        par_root,
        "parLine",
        {"line_RPu": "0.01", "line_XPu": "{{line_XPu}}", "line_BPu": "0", "line_GPu": "0"},
    )

    lines = model_parameters._get_line_values(dyd_root, par_root, 0.02, 0.35)

    assert lines[0].r == pytest.approx(0.02)
    assert lines[0].x == pytest.approx(0.35)


def test_get_transformer_values_missing_parset_raises():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "StepUp_Xfmr", "TransformerFixedRatio", "missing")
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        model_parameters._get_transformer_values(dyd_root, par_root, s_nref=90.0)


def test_get_transformer_values_reads_pu_parameters():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "StepUp_Xfmr", "TransformerFixedRatio", "parXfmr")
    _add_connect(dyd_root, "StepUp_Xfmr", "transformer_terminal1", "IntNetwork_Line", "term2")
    _add_connect(dyd_root, "StepUp_Xfmr", "transformer_terminal2", "Wind_Turbine", "term")
    par_root = _make_root()
    _add_parset(
        par_root,
        "parXfmr",
        {
            "transformer_RPu": "0.003",
            "transformer_XPu": "0.027",
            "transformer_BPu": "0.001",
            "transformer_GPu": "0.0",
            "transformer_rTfoPu": "0.9574",
        },
    )

    transformers = model_parameters._get_transformer_values(dyd_root, par_root, s_nref=90.0)

    assert len(transformers) == 1
    xfmr = transformers[0]
    assert xfmr.id == "StepUp_Xfmr"
    assert xfmr.par_id == "parXfmr"
    assert xfmr.r == pytest.approx(0.003)
    assert xfmr.x == pytest.approx(0.027)
    assert xfmr.b == pytest.approx(0.001)
    assert xfmr.g == pytest.approx(0.0)
    assert xfmr.r_tfo == pytest.approx(0.9574)
    assert xfmr.alpha_tfo == pytest.approx(0.0)
    assert xfmr.terminals[0].connected_equipment == "IntNetwork_Line"
    assert xfmr.terminals[1].connected_equipment == "Wind_Turbine"


def test_convert_transformer_units_scales_percent_values(monkeypatch):
    dynawo_names = {
        "Resistance": "transformer_R",
        "Reactance": "transformer_X",
        "Conductance": "transformer_G",
        "Susceptance": "transformer_B",
        "SNom": "transformer_SNom",
    }
    translator_stub = SimpleNamespace(
        get_dynawo_variable=lambda lib, name: (1, dynawo_names[name])
    )
    monkeypatch.setattr(model_parameters, "dynawo_translator", translator_stub)
    par_root = _make_root()
    parset = _add_parset(
        par_root,
        "parXfmr",
        {
            "transformer_R": "0.5",
            "transformer_X": "12.0",
            "transformer_G": "0.0",
            "transformer_B": "2.0",
            "transformer_SNom": "45.0",
        },
    )

    r, x, g, b = model_parameters._convert_transformer_units(
        [parset], {"ns": _NS}, "AnyLib", s_nref=90.0
    )

    assert r == pytest.approx(2.0 * 0.5 / 100)
    assert x == pytest.approx(2.0 * 12.0 / 100)
    assert g == pytest.approx(0.0)
    assert b == pytest.approx(0.5 * 2.0 / 100)


def test_get_load_values_missing_parset_raises():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "Aux_Load", "LoadAlphaBeta", "missing")
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        model_parameters._get_load_values(dyd_root, par_root)


def test_get_load_values_reads_parameters():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "Aux_Load", "LoadAlphaBeta", "parLoad")
    _add_connect(dyd_root, "Aux_Load", "load_terminal", "AuxLoad_Xfmr", "term2")
    par_root = _make_root()
    _add_parset(
        par_root,
        "parLoad",
        {
            "load_P0Pu": "0.02",
            "load_Q0Pu": "0.01",
            "load_U0Pu": "1.05",
            "load_UPhase0": "0.1",
            "load_alpha": "2",
            "load_beta": "2",
        },
    )

    loads = model_parameters._get_load_values(dyd_root, par_root)

    assert len(loads) == 1
    load = loads[0]
    assert load.id == "Aux_Load"
    assert load.lib == "LoadAlphaBeta"
    assert load.par_id == "parLoad"
    assert load.p == pytest.approx(0.02)
    assert load.q == pytest.approx(0.01)
    assert load.u == pytest.approx(1.05)
    assert load.u_phase == pytest.approx(0.1)
    assert load.alpha == pytest.approx(2.0)
    assert load.beta == pytest.approx(2.0)
    assert load.terminals[0].connected_equipment == "AuxLoad_Xfmr"


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


def test_adjust_load_duplicated_parset_raises():
    par_root = _make_root()
    _add_parset(par_root, "Aux_Load", {})
    _add_parset(par_root, "Aux_Load", {})

    with pytest.raises(ValueError, match="Multiple parameter sets with id='Aux_Load' were found"):
        model_parameters._adjust_load(par_root, "Aux_Load", "LoadAlphaBeta", 0.1, 0.05, 1.0, 0.0)


def test_set_parameter_updates_existing_value():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {"generator_P0Pu": "0.5"})

    model_parameters._set_parameter([parset], {"ns": _NS}, "generator_P0Pu", -1, 0.75)

    parameter = parset.xpath("ns:par[@name='generator_P0Pu']", namespaces={"ns": _NS})[0]
    assert parameter.get("value") == "-0.75"


def test_set_parameter_creates_parameter_only_when_requested():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {})

    model_parameters._set_parameter([parset], {"ns": _NS}, "generator_Q0Pu", 1, 0.25)
    model_parameters._set_parameter(
        [parset], {"ns": _NS}, "generator_P0Pu", 1, 0.5, create_if_missing=True
    )

    assert [par.get("name") for par in parset] == ["generator_P0Pu"]
    created = next(par for par in parset if par.get("name") == "generator_P0Pu")
    assert created.get("type") == "DOUBLE"
    assert created.get("value") == "0.5"


def test_set_parameter_without_name_is_noop():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {})

    model_parameters._set_parameter([parset], {"ns": _NS}, None, 1, 0.5, create_if_missing=True)

    assert len(parset) == 0


def test_get_parameter_reads_value_and_sign():
    par_root = _make_root()
    parset = _add_parset(par_root, "parLoad", {"load_U0Pu": "1.02"})

    sign, value = model_parameters._get_parameter(
        [parset], {"ns": _NS}, "LoadAlphaBeta", "Voltage0"
    )

    assert sign == 1
    assert value == "1.02"


def test_get_parameter_missing_par_returns_none_value():
    par_root = _make_root()
    parset = _add_parset(par_root, "parLoad", {})

    sign, value = model_parameters._get_parameter(
        [parset], {"ns": _NS}, "LoadAlphaBeta", "Voltage0"
    )

    assert sign == 1
    assert value is None


def test_get_parameter_unknown_variable_returns_none():
    par_root = _make_root()
    parset = _add_parset(par_root, "parLoad", {"load_U0Pu": "1.02"})

    sign, value = model_parameters._get_parameter(
        [parset], {"ns": _NS}, "LoadAlphaBeta", "NoSuchToolVariable"
    )

    assert sign is None
    assert value is None


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


def test_get_generator_ppc_local_reads_a_declared_true():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {"WT4B_PPCLocal": "true"})

    ppc_local = model_parameters._get_generator_ppc_local(
        [parset], {"ns": _NS}, "WT4BWeccCurrentSource"
    )

    assert ppc_local is True


def test_get_generator_ppc_local_reads_a_declared_false():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {"WT4B_PPCLocal": "false"})

    ppc_local = model_parameters._get_generator_ppc_local(
        [parset], {"ns": _NS}, "WT4BWeccCurrentSource"
    )

    assert ppc_local is False


def test_get_generator_ppc_local_defaults_to_true_when_the_parameter_is_absent():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {})

    ppc_local = model_parameters._get_generator_ppc_local(
        [parset], {"ns": _NS}, "IECWT4ACurrentSource2015"
    )

    assert ppc_local is True


def test_get_generator_converter_lv_control_reads_a_declared_false():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {"WTG4B_ConverterLVControl": "false"})

    converter_lv_control = model_parameters._get_generator_converter_lv_control(
        [parset], {"ns": _NS}, "WTG4BWeccCurrentSource"
    )

    assert converter_lv_control is False


def test_get_generator_converter_lv_control_defaults_to_true_when_absent():
    par_root = _make_root()
    parset = _add_parset(par_root, "parGen", {})

    converter_lv_control = model_parameters._get_generator_converter_lv_control(
        [parset], {"ns": _NS}, "WTG4BWeccCurrentSource"
    )

    assert converter_lv_control is True


def test_append_generator_takes_ppc_local_from_the_par_file():
    dyd_root = _make_root()
    model_parameter = _add_bbmodel(dyd_root, "Wind_Turbine", "WT4BWeccCurrentSource", "parGen")
    _add_connect(dyd_root, "Wind_Turbine", "WT4B_terminal", "StepUp_Xfmr", "transformer_terminal2")
    par_root = _make_root()
    _add_parset(par_root, "parGen", {"WT4B_PPCLocal": "false"})
    generators = []

    model_parameters._append_generator(dyd_root, par_root, model_parameter, generators)

    assert len(generators) == 1
    assert generators[0].ppc_local is False
    assert generators[0].terminals[0].connected_equipment == "StepUp_Xfmr"


def test_append_generator_defaults_ppc_local_to_true_when_the_par_omits_it():
    dyd_root = _make_root()
    model_parameter = _add_bbmodel(dyd_root, "Wind_Turbine", "IECWT4ACurrentSource2015", "parGen")
    _add_connect(dyd_root, "Wind_Turbine", "WT4A_terminal", "StepUp_Xfmr", "transformer_terminal2")
    par_root = _make_root()
    _add_parset(par_root, "parGen", {})
    generators = []

    model_parameters._append_generator(dyd_root, par_root, model_parameter, generators)

    assert generators[0].ppc_local is True


def _xfmr(id: str) -> SimpleNamespace:
    return SimpleNamespace(id=id)


def test_classify_transformers_routes_each_id_to_its_role():
    group = _xfmr("Group_Xfmr")
    auxload = _xfmr("AuxLoad_Xfmr")
    main = _xfmr("Main_Xfmr")

    by_role = model_parameters._classify_transformers([main, auxload, group])

    assert by_role[model_parameters.GROUP_XFMR_ROLE] == [group]
    assert by_role[model_parameters.AUXLOAD_XFMR_ROLE] == [auxload]
    assert by_role[model_parameters.MAIN_XFMR_ROLE] == [main]


def test_classify_transformers_rejects_the_pre_catalog_unit_id():
    """A pre-catalog StepUp_Xfmr has no role: it is not the Zone-1 group transformer."""
    with pytest.raises(ValueError) as excinfo:
        model_parameters._classify_transformers([_xfmr("StepUp_Xfmr_1")])

    assert "StepUp_Xfmr_1" in str(excinfo.value)


def test_classify_transformers_rejects_an_unknown_id():
    with pytest.raises(ValueError) as excinfo:
        model_parameters._classify_transformers([_xfmr("Some_Xfmr")])

    assert "Some_Xfmr" in str(excinfo.value)
    assert "Group_Xfmr" in str(excinfo.value)
