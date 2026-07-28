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

from dycov.files import producer_dyd_file
from dycov.files.producer_dyd_file import check_dynamic_models, create_producer_dyd_file


@pytest.fixture(autouse=True)
def patch_dynawo_translator(monkeypatch):
    class DummySection:
        def sections(self):
            return [
                "BUS_DYNAMIC_MODEL",
                "SM_DYNAMIC_MODEL",
                "PPM_DYNAMIC_MODEL",
                "BESS_DYNAMIC_MODEL",
                "LINE_DYNAMIC_MODEL",
                "LOAD_DYNAMIC_MODEL",
                "XFMR_DYNAMIC_MODEL",
            ]

    class DummyTranslator:
        def get_bus_models(self):
            return ["BUS_DYNAMIC_MODEL"]

        def get_synchronous_machine_models(self):
            return ["SM_DYNAMIC_MODEL"]

        def get_power_park_models(self):
            return ["PPM_DYNAMIC_MODEL"]

        def get_storage_models(self):
            return ["BESS_DYNAMIC_MODEL"]

        def get_line_models(self):
            return ["LINE_DYNAMIC_MODEL"]

        def get_load_models(self):
            return ["LOAD_DYNAMIC_MODEL"]

        def get_transformer_models(self):
            return ["XFMR_DYNAMIC_MODEL"]

    monkeypatch.setattr(producer_dyd_file, "dynawo_translator", DummyTranslator())
    yield


def test_create_producer_dyd_file_performance_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        create_producer_dyd_file(target, "S", "performance_SM")
        dyd_path = target / "Producer.dyd"
        assert dyd_path.exists()
        tree = etree.parse(str(dyd_path))
        root = tree.getroot()
        assert root.tag.endswith("dynamicModelsArchitecture")
        comments = [e for e in root.iter() if isinstance(e, etree._Comment)]
        assert any("Topology: S" in c.text for c in comments)
        ns = etree.QName(root).namespace
        bbmodels = list(root.iterfind(f"{{{ns}}}blackBoxModel"))
        assert len(bbmodels) > 0


def test_check_dynamic_models_all_supported():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        create_producer_dyd_file(target, "S", "performance_SM")
        assert check_dynamic_models(target, "performance_SM") is True


def test_create_producer_dyd_file_invalid_topology():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        with pytest.raises(ValueError) as excinfo:
            create_producer_dyd_file(target, "INVALID_TOPO", "performance_SM")
        assert "Select one of the 8 available topologies" in str(excinfo.value)


def test_create_producer_dyd_file_invalid_template():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        with pytest.raises(ValueError) as excinfo:
            create_producer_dyd_file(target, "S", "unsupported_template")
        assert "Unsupported template name" in str(excinfo.value)


def _connects(dyd_path):
    root = etree.parse(str(dyd_path)).getroot()
    ns = etree.QName(root).namespace
    return [
        (c.get("id1"), c.get("var1"), c.get("id2"), c.get("var2"))
        for c in root.iterfind(f"{{{ns}}}connect")
    ]


def test_performance_ppm_has_remote_control():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        create_producer_dyd_file(target, "S", "performance_PPM")
        conns = _connects(target / "Producer.dyd")
        assert any(i1 == "Measurements" and "PPccPu" in (v2 or "") for i1, _, _, v2 in conns)
        assert any(i1 == "Measurements" and "QPccPu" in (v2 or "") for i1, _, _, v2 in conns)
        assert any(i1 == "BusPDR" and "uPccPu_re" in (v2 or "") for i1, _, _, v2 in conns)
        assert any(i1 == "BusPDR" and "uPccPu_im" in (v2 or "") for i1, _, _, v2 in conns)
        assert check_dynamic_models(target, "performance_PPM") is True


def test_performance_sm_has_no_remote_control():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        create_producer_dyd_file(target, "S", "performance_SM")
        conns = _connects(target / "Producer.dyd")
        assert not any(i1 == "Measurements" for i1, _, _, _ in conns)


def test_model_ppm_remote_control_only_in_zone3():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        (target / "Zone1").mkdir()
        (target / "Zone3").mkdir()
        create_producer_dyd_file(target, "S", "model_PPM")
        z1 = _connects(target / "Zone1" / "Producer.dyd")
        z3 = _connects(target / "Zone3" / "Producer.dyd")
        assert not any(i1 == "Measurements" for i1, _, _, _ in z1)
        assert any(i1 == "Measurements" for i1, _, _, _ in z3)


def test_fill_producer_dyd_injects_libs_and_terminal():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        create_producer_dyd_file(target, "S", "performance_PPM")
        dyd_path = target / "Producer.dyd"
        gen = producer_dyd_file.PPM_ID
        producer_dyd_file.fill_producer_dyd(
            dyd_path,
            libs={
                "StepUp_Xfmr": "TransformerRatioTapChanger",
                gen: "PhotovoltaicsWeccCurrentSource",
            },
            terminals={gen: "photovoltaics_terminal"},
        )
        root = etree.parse(str(dyd_path)).getroot()
        ns = etree.QName(root).namespace
        libs = {b.get("id"): b.get("lib") for b in root.iterfind(f"{{{ns}}}blackBoxModel")}
        assert libs["StepUp_Xfmr"] == "TransformerRatioTapChanger"
        assert libs[gen] == "PhotovoltaicsWeccCurrentSource"
        conns = _connects(dyd_path)
        # terminal placeholder replaced, and the remote-control ports derived from it
        assert any(v == "photovoltaics_terminal" for _, v, _, _ in conns)
        assert any(v2 == "photovoltaics_uPccPu_re" for _, _, _, v2 in conns)
        assert any(v2 == "photovoltaics_PPccPu" for _, _, _, v2 in conns)
        assert not any("PPM_" in (v2 or "") for _, _, _, v2 in conns)


def test_check_dynamic_models_with_unsupported_models():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        create_producer_dyd_file(target, "S", "performance_SM")
        dyd_path = target / "Producer.dyd"
        # Parse and modify the DYD file to insert an unsupported model
        tree = etree.parse(str(dyd_path))
        root = tree.getroot()
        ns = etree.QName(root).namespace
        etree.SubElement(
            root,
            f"{{{ns}}}blackBoxModel",
            id="Unsupported",
            lib="UNSUPPORTED_MODEL",
            parFile="Producer.par",
            parId="Unsupported",
        )
        tree.write(str(dyd_path), encoding="utf-8", pretty_print=True, xml_declaration=True)
        assert check_dynamic_models(target, "performance_SM") is False
