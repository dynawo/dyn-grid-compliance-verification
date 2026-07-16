#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
from pathlib import Path

from lxml import etree

from dycov.files.producer_par_file import check_parameters, create_producer_par_file


class TestProducerParFile:
    def _write_dyd(self, path, bbmodels):
        ns = "http://www.rte-france.com/dynawo"
        root = etree.Element(f"{{{ns}}}root", nsmap={None: ns})
        for bb in bbmodels:
            attrib = {k: v for k, v in bb.items() if v is not None}
            etree.SubElement(root, f"{{{ns}}}blackBoxModel", attrib=attrib)
        tree = etree.ElementTree(root)
        tree.write(path, encoding="utf-8", pretty_print=True, xml_declaration=True)

    def _write_desc_xml(self, path, params):
        ns = "http://www.rte-france.com/dynawo"
        root = etree.Element(f"{{{ns}}}modelDescription", nsmap={None: ns})
        for p in params:
            attrib = {
                "name": p["name"],
                "valueType": p["type"],
                "readOnly": "false" if not p.get("readOnly", False) else "true",
            }
            if "defaultValue" in p:
                attrib["defaultValue"] = p["defaultValue"]
            etree.SubElement(root, f"{{{ns}}}parameter", attrib=attrib)
        tree = etree.ElementTree(root)
        tree.write(path, encoding="utf-8", pretty_print=True, xml_declaration=True)

    def _setup_ddb(self, tmp_path, lib_name, params):
        ddb_dir = tmp_path / "ddb"
        ddb_dir.mkdir()
        desc_path = ddb_dir / f"{lib_name}.desc.xml"
        self._write_desc_xml(desc_path, params)
        return ddb_dir

    def _parse_par_sets(self, par_file):
        root = etree.parse(par_file).getroot()
        ns = etree.QName(root).namespace
        return list(root.iterfind(f"{{{ns}}}set")), ns

    def test_create_par_file_performance_sm_happy_path(self, tmp_path, monkeypatch):
        dyd_dir = tmp_path
        dyd_file = dyd_dir / "Producer.dyd"
        bbmodels = [{"id": "BB1", "lib": "libA", "parId": "parA"}]
        self._write_dyd(dyd_file, bbmodels)

        params = [
            {"name": "param1", "type": "double", "defaultValue": "1.0"},
            {"name": "param2", "type": "int", "defaultValue": "2"},
        ]
        ddb_dir = self._setup_ddb(tmp_path, "libA", params)

        from dycov.files import producer_par_file

        monkeypatch.setattr(producer_par_file, "_get_ddb_model_path", lambda _: ddb_dir)

        create_producer_par_file(
            launcher_dwo=Path("dummy_launcher"),
            target=dyd_dir,
            topology="S",
            template="performance_SM",
        )

        par_file = dyd_dir / "Producer.par"
        assert par_file.exists()
        sets, ns = self._parse_par_sets(par_file)
        assert len(sets) == 1
        pars = list(sets[0].iterfind(f"{{{ns}}}par"))
        assert len(pars) == 2
        assert {p.get("name"): p.get("value") for p in pars} == {"param1": "1.0", "param2": "2"}

    def test_create_par_files_model_ppm_zones_happy_path(self, tmp_path, monkeypatch):
        zone1 = tmp_path / "Zone1"
        zone3 = tmp_path / "Zone3"
        zone1.mkdir()
        zone3.mkdir()
        bbmodels = [{"id": "BB1", "lib": "libA", "parId": "parA"}]
        self._write_dyd(zone1 / "Producer.dyd", bbmodels)
        self._write_dyd(zone3 / "Producer.dyd", bbmodels)
        params = [{"name": "p", "type": "double", "defaultValue": "3.14"}]
        ddb_dir = self._setup_ddb(tmp_path, "libA", params)
        from dycov.files import producer_par_file

        monkeypatch.setattr(producer_par_file, "_get_ddb_model_path", lambda _: ddb_dir)
        create_producer_par_file(
            launcher_dwo=Path("dummy_launcher"),
            target=tmp_path,
            topology="S",
            template="model_PPM",
        )
        for zone in [zone1, zone3]:
            par_file = zone / "Producer.par"
            assert par_file.exists()
            sets, ns = self._parse_par_sets(par_file)
            assert len(sets) == 1
            pars = list(sets[0].iterfind(f"{{{ns}}}par"))
            assert len(pars) == 1
            assert pars[0].get("name") == "p"
            assert pars[0].get("value") == "3.14"

    def test_check_parameters_all_values_present(self, tmp_path, monkeypatch):
        dyd_file = tmp_path / "Producer.dyd"
        bbmodels = [{"id": "BB1", "lib": "libA", "parId": "parA"}]
        self._write_dyd(dyd_file, bbmodels)
        params = [
            {"name": "p1", "type": "double", "defaultValue": "1.0"},
            {"name": "p2", "type": "int", "defaultValue": "2"},
        ]
        ddb_dir = self._setup_ddb(tmp_path, "libA", params)
        from dycov.files import producer_par_file

        monkeypatch.setattr(producer_par_file, "_get_ddb_model_path", lambda _: ddb_dir)
        create_producer_par_file(
            launcher_dwo=Path("dummy_launcher"),
            target=tmp_path,
            topology="S",
            template="performance_SM",
        )
        assert check_parameters(tmp_path, "performance_SM") is True

    def test_missing_desc_xml_file_handling(self, tmp_path, capsys, monkeypatch):
        # DYD with a blackBoxModel whose lib does not have a desc.xml
        dyd_file = tmp_path / "Producer.dyd"
        bbmodels = [{"id": "BB1", "lib": "libMissing", "parId": "parA"}]
        self._write_dyd(dyd_file, bbmodels)
        # ddb exists but no desc.xml for libMissing
        ddb_dir = tmp_path / "ddb"
        ddb_dir.mkdir()
        from dycov.files import producer_par_file

        monkeypatch.setattr(producer_par_file, "_get_ddb_model_path", lambda _: ddb_dir)
        create_producer_par_file(
            launcher_dwo=Path("dummy_launcher"),
            target=tmp_path,
            topology="S",
            template="performance_SM",
        )
        # Producer.par should exist but be empty (no <set>)
        par_file = tmp_path / "Producer.par"
        assert par_file.exists()
        sets, _ = self._parse_par_sets(par_file)
        assert len(sets) == 0

    def test_check_parameters_with_empty_values(self, tmp_path, monkeypatch, capture_error_logs):
        dyd_file = tmp_path / "Producer.dyd"
        bbmodels = [{"id": "BB1", "lib": "libA", "parId": "parA"}]
        self._write_dyd(dyd_file, bbmodels)
        params = [
            {"name": "p1", "type": "double", "defaultValue": "1.0"},
            {"name": "p2", "type": "int"},  # No defaultValue
        ]
        ddb_dir = self._setup_ddb(tmp_path, "libA", params)
        from dycov.files import producer_par_file

        monkeypatch.setattr(producer_par_file, "_get_ddb_model_path", lambda _: ddb_dir)
        create_producer_par_file(
            launcher_dwo=Path("dummy_launcher"),
            target=tmp_path,
            topology="S",
            template="performance_SM",
        )

        result = check_parameters(tmp_path, "performance_SM")
        assert result is False
        assert any("parameters without value" in msg for msg in capture_error_logs)
        assert "p2" in capture_error_logs[0]

    def test_blackboxmodel_without_parid(self, tmp_path, monkeypatch):
        dyd_file = tmp_path / "Producer.dyd"
        bbmodels = [
            {"id": "BB1", "lib": "libA", "parId": "parA"},
            {"id": "BB2", "lib": "libB", "parId": None},
        ]
        self._write_dyd(dyd_file, bbmodels)
        params = [{"name": "p", "type": "double", "defaultValue": "1.0"}]
        ddb_dir = self._setup_ddb(tmp_path, "libA", params)
        from dycov.files import producer_par_file

        monkeypatch.setattr(producer_par_file, "_get_ddb_model_path", lambda _: ddb_dir)
        create_producer_par_file(
            launcher_dwo=Path("dummy_launcher"),
            target=tmp_path,
            topology="S",
            template="performance_SM",
        )
        # Only one <set> should be present (for BB1)
        par_file = tmp_path / "Producer.par"
        assert par_file.exists()
        sets, _ = self._parse_par_sets(par_file)
        assert len(sets) == 1
        assert sets[0].get("id") == "parA"
