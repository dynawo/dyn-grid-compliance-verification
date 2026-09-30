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

import pytest
from lxml import etree

from dycov.core.global_variables import ELECTRIC_PERFORMANCE_SM, MODEL_VALIDATION_PPM
from dycov.curves.dynawo.io.crv import create_curves_file


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
        xfmrs = [DummyEquipment("Xfmr", lib="TransformerFixedRatio")]
        generators = [DummyEquipment("Gen", lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a")]
        tso_loads = []
        tso_generators = []
        sim_type = ELECTRIC_PERFORMANCE_SM
        zone = 1
        control_mode = "USetpoint"
        curves_dict = create_curves_file(
            path,
            curves_filename,
            xfmrs,
            generators,
            tso_loads,
            tso_generators,
            sim_type,
            zone,
            control_mode,
        )
        xml_path = path / curves_filename
        assert xml_path.exists()
        root = parse_curves_file(xml_path)
        curve_models = [
            c.attrib["model"] for c in root.findall(".//{http://www.rte-france.com/dynawo}curve")
        ]
        assert "Measurements" in curve_models
        assert "Gen" in curve_models
        assert any("Gen" in k for k in curves_dict)
        assert any("Measurements" in k for k in curves_dict)


def test_create_curves_file_with_all_equipment_types():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        curves_filename = "curves_all.xml"
        xfmrs = [DummyEquipment("Xfmr", lib="TransformerFixedRatio")]
        generators = [DummyEquipment("Gen", lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a")]
        tso_loads = [DummyEquipment("Load", lib="LoadAlphaBeta")]
        tso_generators = []
        sim_type = ELECTRIC_PERFORMANCE_SM
        zone = 1
        control_mode = "USetpoint"
        curves_dict = create_curves_file(
            path,
            curves_filename,
            xfmrs,
            generators,
            tso_loads,
            tso_generators,
            sim_type,
            zone,
            control_mode,
        )
        xml_path = path / curves_filename
        assert xml_path.exists()
        root = parse_curves_file(xml_path)
        models = [
            c.attrib["model"] for c in root.findall(".//{http://www.rte-france.com/dynawo}curve")
        ]
        assert "Measurements" in models
        assert "Gen" in models
        assert any("Measurements" in k for k in curves_dict)
        assert any("Gen" in k for k in curves_dict)


def test_zone_1_asks_the_infinite_bus_for_no_curve(tmp_path):
    curves_dict = create_curves_file(
        tmp_path,
        "curves_z1.xml",
        [DummyEquipment("Xfmr", lib="TransformerFixedRatio")],
        [DummyEquipment("Gen", lib="GeneratorSynchronousFourWindingsTGov1SexsPss2a")],
        [],
        [],
        ELECTRIC_PERFORMANCE_SM,
        1,
        "USetpoint",
    )

    root = parse_curves_file(tmp_path / "curves_z1.xml")
    models = [
        c.attrib["model"] for c in root.findall(".//{http://www.rte-france.com/dynawo}curve")
    ]
    assert "InfiniteBus" not in models
    assert not any("InfiniteBus" in key for key in curves_dict)


def _zone_1_setpoints(tmp_path: Path, control_mode: str) -> set:
    """The setpoints Zone 1 asks the simulation of a unit whose model carries the reactive power
    and the voltage setpoints in a single variable."""
    curves_dict = create_curves_file(
        tmp_path,
        "curves_z1.xml",
        [],
        [DummyEquipment("WT", lib="WT4BWeccCurrentSource")],
        [],
        [],
        MODEL_VALIDATION_PPM,
        1,
        control_mode,
    )
    return {key for key in curves_dict if key.startswith("WT_GEN_") and key.endswith("SetpointPu")}


def test_zone_1_asks_for_the_voltage_setpoint_in_the_test_that_steps_it(tmp_path):
    """#554: in a voltage setpoint step the shared variable is the voltage setpoint."""
    assert _zone_1_setpoints(tmp_path, "USetpoint") == {
        "WT_GEN_ActivePowerSetpointPu",
        "WT_GEN_VoltageSetpointPu",
    }


@pytest.mark.parametrize("control_mode", ["PSetpoint", "QSetpoint", "Others", None])
def test_zone_1_asks_no_other_test_for_the_voltage_setpoint(tmp_path, control_mode):
    """#554: anywhere else the shared variable would be published under both names."""
    assert _zone_1_setpoints(tmp_path, control_mode) == {
        "WT_GEN_ActivePowerSetpointPu",
        "WT_GEN_ReactivePowerSetpointPu",
    }


def test_create_curves_file_invalid_sim_type_and_zone():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        curves_filename = "curves_invalid.xml"
        xfmrs = []
        generators = []
        tso_loads = []
        tso_generators = []
        sim_type = 999  # Invalid sim_type
        zone = 999  # Invalid zone
        control_mode = "USetpoint"
        curves_dict = create_curves_file(
            path,
            curves_filename,
            xfmrs,
            generators,
            tso_loads,
            tso_generators,
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
        allowed = {"Measurements"}
        assert (not models) or set(models).issubset(allowed)
        # Dictionary should be minimal or empty
        assert isinstance(curves_dict, dict)
        assert len(curves_dict) <= 6
