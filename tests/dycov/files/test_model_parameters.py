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
        def get_generator_parameters(self, generator, control_mode, zone):
            return ["MwpqMode", "MqG"]

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
    model_parameters._apply_control_mode(DummyGen(), parset_elem, nsmap, "USetpoint", 3)


def test_get_grid_load():
    from dycov.model.parameters import LoadInit

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
    ns = "http://x"
    root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})

    etree.SubElement(root, f"{{{ns}}}outputs", directory="outdir")

    f = tmp_path / "file.jobs"
    etree.ElementTree(root).write(str(tmp_path / "file.jobs"))

    res = model_parameters.find_output_dir(tmp_path, "file")

    assert res == "outdir"


def test_extract_defined_value_errors():
    with pytest.raises(ValueError):
        model_parameters.extract_defined_value("", "p", 1)

    with pytest.raises(ValueError):
        model_parameters.extract_defined_value("abc", "p", 1)

    with pytest.raises(ValueError):
        model_parameters.extract_defined_value("2*x", "p", 1)


def test_extract_defined_value_numeric():
    val = model_parameters.extract_defined_value("2.5", "p", 1)

    assert val == pytest.approx(2.5)
