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
from types import SimpleNamespace

import pytest
from lxml import etree

from dycov.files import model_parameters, par_access

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


def testget_line_values_missing_parset_raises():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "IntNetwork_Line", "Line", "missing")
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        model_parameters.get_line_values(dyd_root, par_root, None, None)


def testget_line_values_reads_parameters():
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

    lines = model_parameters.get_line_values(dyd_root, par_root, None, None)

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


def testget_line_values_applies_provided_impedances():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "IntNetwork_Line", "Line", "parLine")
    par_root = _make_root()
    _add_parset(
        par_root,
        "parLine",
        {"line_RPu": "0.01", "line_XPu": "{{line_XPu}}", "line_BPu": "0", "line_GPu": "0"},
    )

    lines = model_parameters.get_line_values(dyd_root, par_root, 0.02, 0.35)

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
    monkeypatch.setattr(par_access, "dynawo_translator", translator_stub)
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


def testget_load_values_missing_parset_raises():
    dyd_root = _make_root()
    _add_bbmodel(dyd_root, "Aux_Load", "LoadAlphaBeta", "missing")
    par_root = _make_root()

    with pytest.raises(ValueError, match="parameter set with id='missing' was not found"):
        model_parameters.get_load_values(dyd_root, par_root)


def testget_load_values_reads_parameters():
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

    loads = model_parameters.get_load_values(dyd_root, par_root)

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


def testappend_generator_takes_ppc_local_from_the_par_file():
    dyd_root = _make_root()
    model_parameter = _add_bbmodel(dyd_root, "Wind_Turbine", "WT4BWeccCurrentSource", "parGen")
    _add_connect(dyd_root, "Wind_Turbine", "WT4B_terminal", "StepUp_Xfmr", "transformer_terminal2")
    par_root = _make_root()
    _add_parset(par_root, "parGen", {"WT4B_PPCLocal": "false"})
    generators = []

    model_parameters.append_generator(dyd_root, par_root, model_parameter, generators)

    assert len(generators) == 1
    assert generators[0].ppc_local is False
    assert generators[0].terminals[0].connected_equipment == "StepUp_Xfmr"


def testappend_generator_defaults_ppc_local_to_true_when_the_par_omits_it():
    dyd_root = _make_root()
    model_parameter = _add_bbmodel(dyd_root, "Wind_Turbine", "IECWT4ACurrentSource2015", "parGen")
    _add_connect(dyd_root, "Wind_Turbine", "WT4A_terminal", "StepUp_Xfmr", "transformer_terminal2")
    par_root = _make_root()
    _add_parset(par_root, "parGen", {})
    generators = []

    model_parameters.append_generator(dyd_root, par_root, model_parameter, generators)

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
