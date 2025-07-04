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
    # Write CurvesFiles.ini with all values and create referenced files
    ini_content = "[Curves-Files]\n" "curve1 = file1.txt\n" "curve2 = file2.txt\n"
    (temp_model_dir / "CurvesFiles.ini").write_text(ini_content)
    (temp_model_dir / "file1.txt").write_text("dummy")
    (temp_model_dir / "file2.txt").write_text("dummy")
    assert check_curves(temp_model_dir) is True


def test_check_curves_missing_parameter_values(temp_model_dir):
    # Write CurvesFiles.ini with an empty value
    ini_content = "[Curves-Files]\n" "curve1 = file1.txt\n" "curve2 = \n"
    (temp_model_dir / "CurvesFiles.ini").write_text(ini_content)
    (temp_model_dir / "file1.txt").write_text("dummy")
    # Patch dycov_logging to capture error logs
    from dycov.logging import logging as dycov_logging_mod

    logs = []

    class DummyLogger:
        def error(self, msg):
            logs.append(msg)

    orig_get_logger = dycov_logging_mod.dycov_logging.get_logger
    dycov_logging_mod.dycov_logging.get_logger = lambda name: DummyLogger()
    try:
        result = check_curves(temp_model_dir)
        assert result is False
        assert any("parameters without value" in log for log in logs)
    finally:
        dycov_logging_mod.dycov_logging.get_logger = orig_get_logger


def test_check_curves_missing_files(temp_model_dir):
    # Write CurvesFiles.ini referencing a missing file
    ini_content = "[Curves-Files]\n" "curve1 = file1.txt\n" "curve2 = file2.txt\n"
    (temp_model_dir / "CurvesFiles.ini").write_text(ini_content)
    (temp_model_dir / "file1.txt").write_text("dummy")
    # Patch dycov_logging to capture error logs
    from dycov.logging import logging as dycov_logging_mod

    logs = []

    class DummyLogger:
        def error(self, msg):
            logs.append(msg)

    orig_get_logger = dycov_logging_mod.dycov_logging.get_logger
    dycov_logging_mod.dycov_logging.get_logger = lambda name: DummyLogger()
    try:
        result = check_curves(temp_model_dir)
        assert result is False
        assert any("curve files exist" in log for log in logs)
    finally:
        dycov_logging_mod.dycov_logging.get_logger = orig_get_logger


def test_create_producer_curves_unknown_template(temp_model_dir):
    create_producer_curves(temp_model_dir, temp_model_dir, "unknown_template")
    ini_file = temp_model_dir / "Producer" / "CurvesFiles.ini"
    assert not ini_file.exists()
