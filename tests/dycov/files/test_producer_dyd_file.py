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
        # Check that topology comment is present
        comments = [e for e in root.iter() if isinstance(e, etree._Comment)]
        assert any("Topology: S" in c.text for c in comments)
        # Check that at least one blackBoxModel is present
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


def test_check_dynamic_models_with_unsupported_models():
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir)
        create_producer_dyd_file(target, "S", "performance_SM")
        dyd_path = target / "Producer.dyd"
        # Parse and modify the DYD file to insert an unsupported model
        tree = etree.parse(str(dyd_path))
        root = tree.getroot()
        ns = etree.QName(root).namespace
        # Add a blackBoxModel with unsupported lib
        etree.SubElement(
            root,
            f"{{{ns}}}blackBoxModel",
            id="Unsupported",
            lib="UNSUPPORTED_MODEL",
            parFile="Producer.par",
            parId="Unsupported",
        )
        tree.write(str(dyd_path), encoding="utf-8", pretty_print=True, xml_declaration=True)
        # Now check_dynamic_models should return False
        assert check_dynamic_models(target, "performance_SM") is False
