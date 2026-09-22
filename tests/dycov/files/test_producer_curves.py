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

TAP_CHANGER = "TransformerRatioTapChanger"
FIXED_RATIO = "TransformerFixedRatio"


def _write_producer_dyd(
    path: Path, transformer_ids=None, generator_ids=None, lib_type="WTG4AWeccCurrentSource"
):
    """
    Helper to write a minimal Producer.dyd file with given transformer and generator ids.
    """
    root = etree.Element("dynamics", nsmap={None: "http://www.rte-france.com/dynawo"})
    if transformer_ids:
        for entry in transformer_ids:
            tid, lib = entry if isinstance(entry, tuple) else (entry, "TransformerFixedRatio")
            etree.SubElement(root, "blackBoxModel", id=tid, lib=lib)
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


def _curves_for(temp_model_dir, transformer_ids) -> str:
    """Generates the curves file for a producer with the given transformers."""
    curves_path = temp_model_dir / "curves"
    (curves_path / "Producer").mkdir(parents=True)
    _write_producer_dyd(
        temp_model_dir / "Producer.dyd",
        transformer_ids=transformer_ids,
        generator_ids=["Power_Park"],
    )

    create_producer_curves(temp_model_dir, curves_path, "performance_PPM")

    return _read_curves_file(curves_path)


def test_create_producer_curves_offers_the_tap_of_a_tap_changer(temp_model_dir):
    content = _curves_for(
        temp_model_dir,
        [("Main_Xfmr", TAP_CHANGER), ("AuxLoad_Xfmr", FIXED_RATIO)],
    )

    assert "Main_Xfmr_XFMR_Tap" in content
    assert "AuxLoad_Xfmr_XFMR_Tap" not in content


def test_create_producer_curves_skips_a_fixed_ratio_main_transformer(temp_model_dir):
    """The main transformer has no tap unless it is declared as a tap changer."""
    content = _curves_for(temp_model_dir, [("Main_Xfmr", FIXED_RATIO)])

    assert "_XFMR_Tap" not in content


def test_create_producer_curves_offers_the_tap_of_a_group_transformer(temp_model_dir):
    """Any block may be declared a tap changer, and then its tap is a producer curve."""
    content = _curves_for(
        temp_model_dir,
        [("Main_Xfmr", FIXED_RATIO), ("Group_Xfmr", TAP_CHANGER)],
    )

    assert "Group_Xfmr_XFMR_Tap" in content
    assert "Main_Xfmr_XFMR_Tap" not in content
