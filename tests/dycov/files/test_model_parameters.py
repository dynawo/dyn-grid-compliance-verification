#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import configparser

import pytest
from lxml import etree

from dycov.files import model_parameters


def create_simple_dyd_and_par(
    tmp_path, gen_id="Gen1", xfmr_id="StepUp_Xfmr1", load_id="Aux_Load", line_id="IntNetwork_Line"
):
    # DYD XML
    ns = "http://www.rte-france.com/dynawo"
    dyd_root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    # Generator
    etree.SubElement(
        dyd_root,
        f"{{{ns}}}blackBoxModel",
        id=gen_id,
        lib="WTG4AWeccCurrentSource1",
        parId="parGen",
    )
    # Transformer
    etree.SubElement(
        dyd_root, f"{{{ns}}}blackBoxModel", id=xfmr_id, lib="XfmrLib", parId="parXfmr"
    )
    # Load
    etree.SubElement(
        dyd_root, f"{{{ns}}}blackBoxModel", id=load_id, lib="LoadLib", parId="parLoad"
    )
    # Line
    etree.SubElement(
        dyd_root, f"{{{ns}}}blackBoxModel", id=line_id, lib="LineLib", parId="parLine"
    )
    # Connections
    etree.SubElement(dyd_root, f"{{{ns}}}connect", id1=gen_id, id2=xfmr_id)
    etree.SubElement(dyd_root, f"{{{ns}}}connect", id1=load_id, id2=xfmr_id)
    etree.SubElement(dyd_root, f"{{{ns}}}connect", id1=line_id, id2="BusPDR")
    # Write DYD
    dyd_path = tmp_path / "producer.dyd"
    etree.ElementTree(dyd_root).write(
        str(dyd_path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )

    # PAR XML
    par_root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    # Generator params
    set_gen = etree.SubElement(par_root, f"{{{ns}}}set", id="parGen")
    etree.SubElement(set_gen, f"{{{ns}}}par", name="InjectedCurrentMax", value="100.0")
    etree.SubElement(set_gen, f"{{{ns}}}par", name="ActivePower0Pu", value="0.1")
    etree.SubElement(set_gen, f"{{{ns}}}par", name="ReactivePower0Pu", value="0.05")
    etree.SubElement(set_gen, f"{{{ns}}}par", name="VoltageDroop", value="0.01")
    etree.SubElement(set_gen, f"{{{ns}}}par", name="NominalApparentPower", value="90")
    # Transformer params
    set_xfmr = etree.SubElement(par_root, f"{{{ns}}}set", id="parXfmr")
    etree.SubElement(set_xfmr, f"{{{ns}}}par", name="Resistance", value="0.0003")
    etree.SubElement(set_xfmr, f"{{{ns}}}par", name="Reactance", value="0.0268")
    etree.SubElement(set_xfmr, f"{{{ns}}}par", name="Conductance", value="0.0")
    etree.SubElement(set_xfmr, f"{{{ns}}}par", name="Susceptance", value="0.0")
    etree.SubElement(set_xfmr, f"{{{ns}}}par", name="SNom", value="90")
    etree.SubElement(set_xfmr, f"{{{ns}}}par", name="Rho", value="0.9574")
    # Load params
    set_load = etree.SubElement(par_root, f"{{{ns}}}set", id="parLoad")
    etree.SubElement(set_load, f"{{{ns}}}par", name="ActivePower0", value="0.1")
    etree.SubElement(set_load, f"{{{ns}}}par", name="ReactivePower0", value="0.05")
    etree.SubElement(set_load, f"{{{ns}}}par", name="Voltage0", value="1.0")
    etree.SubElement(set_load, f"{{{ns}}}par", name="Phase0", value="0.0")
    # Line params
    set_line = etree.SubElement(par_root, f"{{{ns}}}set", id="parLine")
    etree.SubElement(set_line, f"{{{ns}}}par", name="ResistancePu", value="0.01")
    etree.SubElement(set_line, f"{{{ns}}}par", name="ReactancePu", value="0.01")
    etree.SubElement(set_line, f"{{{ns}}}par", name="SusceptancePu", value="0.1")
    etree.SubElement(set_line, f"{{{ns}}}par", name="ConductancePu", value="0.3")
    # Write PAR
    par_path = tmp_path / "producer.par"
    etree.ElementTree(par_root).write(
        str(par_path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )
    return dyd_path, par_path


def test_get_event_times_normal(tmp_path):
    ns = "http://www.rte-france.com/dynawo"
    root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    etree.SubElement(root, f"{{{ns}}}par", name="fault_tBegin", value="1.5")
    etree.SubElement(root, f"{{{ns}}}par", name="event_tEvent", value="2.5")
    par_path = tmp_path / "case1.par"
    etree.ElementTree(root).write(
        str(par_path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )
    t1, t2 = model_parameters.get_event_times(tmp_path, "case1", 0.5, 10.0)
    assert t1 == 1.5
    assert t2 == 2.5


def test_missing_or_malformed_par_values(tmp_path):
    ns = "http://www.rte-france.com/dynawo"
    root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    # Missing fault_tBegin and event_tEvent, only step_tStep present with placeholder
    etree.SubElement(root, f"{{{ns}}}par", name="step_tStep", value="{step}")
    par_path = tmp_path / "case2.par"
    etree.ElementTree(root).write(
        str(par_path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )
    t1, t2 = model_parameters.get_event_times(tmp_path, "case2", 0.5, 10.0)
    assert t1 != t1  # NaN
    assert t2 != t2  # NaN

    # Test extract_defined_value with None value_definition
    with pytest.raises(ValueError):
        model_parameters.extract_defined_value(None, "pmax", 90)


def test_no_matching_equipment_models(tmp_path):
    ns = "http://www.rte-france.com/dynawo"
    dyd_root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    dyd_path = tmp_path / "empty.dyd"
    etree.ElementTree(dyd_root).write(
        str(dyd_path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )
    par_root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    par_path = tmp_path / "empty.par"
    etree.ElementTree(par_root).write(
        str(par_path), pretty_print=True, xml_declaration=True, encoding="utf-8"
    )
    ini_file = configparser.ConfigParser()
    s_nref = 90.0
    result = model_parameters.get_producer_values(dyd_path, par_path, ini_file, s_nref)
    generators, stepup_xfmrs, aux_load, auxload_xfmr, ppm_xfmr, intline = result
    assert generators == []
    assert stepup_xfmrs == []
    assert aux_load is None
    assert auxload_xfmr is None
    assert ppm_xfmr is None
    assert intline is None


def test_extract_defined_value_with_placeholders():
    # Placeholder value
    val = model_parameters.extract_defined_value("2*b", "b", 0.2)
    assert val == pytest.approx(0.4)
    val2 = model_parameters.extract_defined_value("pmax", "pmax", 90)
    assert val2 == pytest.approx(90)
    val3 = model_parameters.extract_defined_value("3*pmax", "pmax", 10)
    assert val3 == pytest.approx(30)


def test_generator_control_mode_selection_and_application(tmp_path, monkeypatch):
    # Setup dummy config and translator
    class DummyConfig:
        def has_key(self, section, key):
            return section == "USetpoint_IEC_" and key == "control_option"

        def get_int(self, section, key, default):
            return 1

        def get_options(self, section):
            return []

        def get_value(self, section, option):
            return None

    class DummyDynawoTranslator:
        def get_control_mode(self, section, control_option):
            return {"MwpqMode": "3"}

        def is_valid_control_mode(self, generator, generator_control_mode, parameters):
            return True, ""

        def get_dynawo_variable(self, lib, name):
            return (1, name)

    monkeypatch.setattr(model_parameters, "config", DummyConfig())
    monkeypatch.setattr(model_parameters, "dynawo_translator", DummyDynawoTranslator())

    class DummyLogger:
        def debug(self, msg):
            pass

        def warning(self, msg):
            pass

        def error(self, msg):
            pass

    class DummyLogging:
        def get_logger(self, name):
            return DummyLogger()

    monkeypatch.setattr(model_parameters, "dycov_logging", DummyLogging())

    # Generator and parset
    class DummyGen:
        lib = "IEC"
        id = "Gen1"
        UseVoltageDroop = False
        par_id = "parGen"

    ns = "http://www.rte-france.com/dynawo"
    par_root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
    parset_elem = etree.SubElement(par_root, f"{{{ns}}}set", id="parGen")
    nsmap = {"ns": ns}
    model_parameters._apply_control_mode(DummyGen(), parset_elem, nsmap, "USetpoint", False, 3)
