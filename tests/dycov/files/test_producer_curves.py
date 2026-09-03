#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2025 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import shutil
import tempfile
from pathlib import Path

import pytest
from lxml import etree

from dycov.files.producer_curves import check_curves, create_producer_curves


def _write_producer_dyd(
    path: Path, transformer_ids=None, generator_ids=None, lib_type="WTG4AWeccCurrentSource"
):
    """
    Helper to write a minimal Producer.dyd file with given transformer and generator ids.
    """
    root = etree.Element("dynamics", nsmap={None: "http://www.rte-france.com/dynawo"})
    if transformer_ids:
        for tid in transformer_ids:
            etree.SubElement(root, "blackBoxModel", id=tid, lib="Transformer")
    if generator_ids:
        for gid in generator_ids:
            etree.SubElement(root, "blackBoxModel", id=gid, lib=lib_type)
    tree = etree.ElementTree(root)
    tree.write(str(path), pretty_print=True, xml_declaration=True, encoding="utf-8")


@pytest.fixture
def temp_model_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d)


def test_check_curves_all_values_and_files_exist(temp_model_dir):
    ini_content = "[Curves-Files]\ncurve1 = file1.txt\ncurve2 = file2.txt\n"
    (temp_model_dir / "CurvesFiles.ini").write_text(ini_content)
    (temp_model_dir / "file1.txt").write_text("dummy")
    (temp_model_dir / "file2.txt").write_text("dummy")
    assert check_curves(temp_model_dir) is True


def test_check_curves_missing_parameter_values(temp_model_dir, capture_error_logs):
    ini_content = "[Curves-Files]\ncurve1 = file1.txt\ncurve2 = \n"
    (temp_model_dir / "CurvesFiles.ini").write_text(ini_content)
    (temp_model_dir / "file1.txt").write_text("dummy")

    assert check_curves(temp_model_dir) is False
    assert any("parameters without value" in log for log in capture_error_logs)


def test_check_curves_missing_files(temp_model_dir, capture_error_logs):
    ini_content = "[Curves-Files]\ncurve1 = file1.txt\ncurve2 = file2.txt\n"
    (temp_model_dir / "CurvesFiles.ini").write_text(ini_content)
    (temp_model_dir / "file1.txt").write_text("dummy")

    assert check_curves(temp_model_dir) is False
    assert any("curve files exist" in log for log in capture_error_logs)


def test_create_producer_curves_unknown_template(temp_model_dir):
    create_producer_curves(temp_model_dir, temp_model_dir, "unknown_template")
    ini_file = temp_model_dir / "Producer" / "CurvesFiles.ini"
    assert not ini_file.exists()


def _read_curves_file(curves_path: Path) -> str:
    return (curves_path / "Producer" / "CurvesFiles.ini").read_text()


def test_create_producer_curves_offers_the_main_transformer_tap(temp_model_dir):
    """The catalog leaves Main_Xfmr as the only transformer in series with the PDR."""
    curves_path = temp_model_dir / "curves"
    (curves_path / "Producer").mkdir(parents=True)
    _write_producer_dyd(
        temp_model_dir / "Producer.dyd",
        transformer_ids=["Main_Xfmr", "AuxLoad_Xfmr"],
        generator_ids=["Power_Park"],
    )

    create_producer_curves(temp_model_dir, curves_path, "performance_PPM")

    content = _read_curves_file(curves_path)
    assert "Main_Xfmr_XFMR_Tap" in content
    assert "AuxLoad_Xfmr_XFMR_Tap" not in content


def test_create_producer_curves_offers_the_group_transformer_tap(temp_model_dir):
    """Zone 1 keeps a group transformer, so its tap is still offered as a curve."""
    curves_path = temp_model_dir / "curves"
    (curves_path / "Producer").mkdir(parents=True)
    _write_producer_dyd(
        temp_model_dir / "Producer.dyd",
        transformer_ids=["Group_Xfmr"],
        generator_ids=["Power_Park"],
    )

    create_producer_curves(temp_model_dir, curves_path, "performance_PPM")

    assert "Group_Xfmr_XFMR_Tap" in _read_curves_file(curves_path)
