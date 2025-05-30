#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
import tempfile
from pathlib import Path

from lxml import etree

from dycov.core.global_variables import ELECTRIC_PERFORMANCE_SM
from dycov.curves.dynawo.crv import create_curves_file


class DummyEquipment:
    def __init__(self, id, lib=None, var=None):
        self.id = id
        self.lib = lib
        self.var = var


def parse_curves_file(path):
    # Helper to parse the generated XML file and return the root element
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(path), parser)
    return tree.getroot()


def test_create_curves_file_electric_performance_sm():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        curves_filename = "curves_sm.xml"
        connected_to_pdr = [DummyEquipment("Xfmr", var="Xfmr_terminal")]
        xfmrs = [DummyEquipment("Xfmr", lib="XfmrLib")]
        generators = [DummyEquipment("Gen", lib="GenLib")]
        rte_loads = []
        sim_type = ELECTRIC_PERFORMANCE_SM
        zone = 1
        control_mode = "USetpoint"
        curves_dict = create_curves_file(
            path,
            curves_filename,
            connected_to_pdr,
            xfmrs,
            generators,
            rte_loads,
            sim_type,
            zone,
            control_mode,
        )
        xml_path = path / curves_filename
        assert xml_path.exists()
        root = parse_curves_file(xml_path)
        print(root)
        # Check that expected curve elements exist
        curve_models = [
            c.attrib["model"] for c in root.findall(".//{http://www.rte-france.com/dynawo}curve")
        ]
        print(curve_models)
        assert "BusPDR" in curve_models
        assert "InfiniteBus" in curve_models
        assert "Xfmr" in curve_models
        assert "Gen" in curve_models
        # Check that dictionary contains expected keys
        assert any("Gen" in k for k in curves_dict)
        assert any("BusPDR" in k for k in curves_dict)
        assert any("Xfmr" in k for k in curves_dict)


def test_create_curves_file_with_all_equipment_types():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        curves_filename = "curves_all.xml"
        connected_to_pdr = [DummyEquipment("Xfmr", var="Xfmr_terminal")]
        xfmrs = [DummyEquipment("Xfmr", lib="XfmrLib")]
        generators = [DummyEquipment("Gen", lib="GenLib")]
        rte_loads = [DummyEquipment("Load", lib="LoadLib")]
        sim_type = ELECTRIC_PERFORMANCE_SM
        zone = 1
        control_mode = "USetpoint"
        curves_dict = create_curves_file(
            path,
            curves_filename,
            connected_to_pdr,
            xfmrs,
            generators,
            rte_loads,
            sim_type,
            zone,
            control_mode,
        )
        xml_path = path / curves_filename
        assert xml_path.exists()
        root = parse_curves_file(xml_path)
        # Check that all equipment types are present in the XML
        models = [
            c.attrib["model"] for c in root.findall(".//{http://www.rte-france.com/dynawo}curve")
        ]
        assert "Xfmr" in models
        assert "Gen" in models
        # Check that dictionary contains entries for all equipment
        assert any("PDR" in k for k in curves_dict)
        assert any("Xfmr" in k for k in curves_dict)
        assert any("Gen" in k for k in curves_dict)


def test_create_curves_file_invalid_sim_type_and_zone():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        curves_filename = "curves_invalid.xml"
        connected_to_pdr = []
        xfmrs = []
        generators = []
        rte_loads = []
        sim_type = 999  # Invalid sim_type
        zone = 999  # Invalid zone
        control_mode = "USetpoint"
        curves_dict = create_curves_file(
            path,
            curves_filename,
            connected_to_pdr,
            xfmrs,
            generators,
            rte_loads,
            sim_type,
            zone,
            control_mode,
        )
        xml_path = path / curves_filename
        assert xml_path.exists()
        root = parse_curves_file(xml_path)
        # Only bus curves should be present (no unintended curves)
        models = [
            c.attrib["model"] for c in root.findall(".//{http://www.rte-france.com/dynawo}curve")
        ]
        assert "BusPDR" in models or "InfiniteBus" in models
        # Dictionary should be minimal or empty
        assert isinstance(curves_dict, dict)
        assert len(curves_dict) <= 4
