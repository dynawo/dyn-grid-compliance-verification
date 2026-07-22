#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

import re
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from dycov.files.manage_files import (
    clone_as_subdirectory,
    copy_file,
    copy_from_path,
    create_dir,
    get_dynawo_version,
    get_latex_version,
    get_uv_version,
    list_directories,
    move_report,
    read_curves,
    remove_dir,
    rename_path,
    should_copy,
)

# =========================
# Versions
# =========================

def test_get_dynawo_version_ok():
    mock_result = Mock(returncode=0, stdout="Dynawo 1.0\nother")

    with patch("subprocess.run", return_value=mock_result):
        res = get_dynawo_version(Path("dynawo"))

    assert res == "Dynawo 1.0"


def test_get_dynawo_version_not_found():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        res = get_dynawo_version(Path("dynawo"))

    assert res == "not found"


def test_get_latex_version_ok():
    mock_result = Mock(returncode=0, stdout="pdfTeX 3.0\n")

    with patch("subprocess.run", return_value=mock_result):
        res = get_latex_version()

    assert res == "pdfTeX 3.0"


def test_get_uv_version_fail():
    mock_result = Mock(returncode=1, stdout="")

    with patch("subprocess.run", return_value=mock_result):
        res = get_uv_version()

    assert res == "not found"


# =========================
# Basic file helpers
# =========================

def test_should_copy(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("x")

    assert should_copy(f) is True
    assert should_copy(f, [re.compile(r".*\.txt")]) is False


def test_copy_file(tmp_path):
    src = tmp_path / "a.txt"
    dst = tmp_path / "b.txt"
    src.write_text("x")

    copy_file(src, dst)

    assert dst.exists()


def test_rename_path(tmp_path):
    src = tmp_path / "a"
    dst = tmp_path / "b"
    src.mkdir()

    rename_path(src, dst)

    assert dst.exists()


def test_create_and_remove_dir(tmp_path):
    d = tmp_path / "dir"

    create_dir(d)
    assert d.exists()

    remove_dir(d)
    assert not d.exists()


# =========================
# Directory helpers
# =========================

def test_list_directories(tmp_path):
    (tmp_path / "d1").mkdir()
    (tmp_path / ".hidden").mkdir()

    res = list_directories(tmp_path)

    assert "d1" in res
    assert ".hidden" not in res


def test_copy_from_path_file(tmp_path):
    src = tmp_path / "a.txt"
    dst = tmp_path / "out"
    dst.mkdir()

    src.write_text("x")

    copy_from_path(src, dst)

    assert (dst / "a.txt").exists()


def test_copy_from_path_dir(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    src.mkdir()
    dst.mkdir()

    f = src / "a.txt"
    f.write_text("x")

    copy_from_path(src, dst)

    assert (dst / "a.txt").exists()


def test_clone_as_subdirectory(tmp_path):
    src = tmp_path / "src"
    src.mkdir()

    f = src / "a.txt"
    f.write_text("x")

    res = clone_as_subdirectory(src, "clone")

    assert res.exists()
    assert (res / "a.txt").exists()


# =========================
# Reports
# =========================

def test_move_report_pdf(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    src.mkdir()
    dst.mkdir()

    pdf = src / "case.pdf"
    pdf.write_text("x")

    res = move_report(src, dst, "case")

    assert res is True
    assert (dst / "case.pdf").exists()


def test_move_report_log(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    src.mkdir()
    dst.mkdir()

    log = src / "case.log"
    log.write_text("x")

    res = move_report(src, dst, "case")

    assert res is False
    assert (dst / "case.log").exists()


# =========================
# Read curves
# =========================

def test_read_curves(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("time;value\n0;1\n1;2")

    df = read_curves(f)

    assert isinstance(df, pd.DataFrame)
    assert "time" in df.columns


# =========================
# Curves copy
# =========================

def test_copy_curve_files_by_name(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    src.mkdir()
    dst.mkdir()

    (src / "curve.csv").write_text("x")
    (src / "curve.dict").write_text("x")

    from dycov.files.manage_files import _copy_curve_files_by_name

    res = _copy_curve_files_by_name(src, dst, "curve")

    assert len(res) == 2
    assert (dst / "curve.csv").exists()


def test_copy_base_curves_files_fail(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    src.mkdir()
    dst.mkdir()

    from dycov.files.manage_files import copy_base_curves_files

    res = copy_base_curves_files(src, dst, "test")

    assert res is False


# =========================
# Config file
# =========================

def test_create_config_file(tmp_path):
    src = tmp_path / "config.ini"
    dst = tmp_path / "out.ini"

    src.write_text("[section]\nvalue=1\nother=2\n")

    from dycov.files.manage_files import create_config_file

    create_config_file(src, dst)

    content = dst.read_text()

    assert "[section]" in content
    assert "# other=2" in content


# =========================
# Output dir
# =========================

def test_check_output_dir_overwrite(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    (d / "file.txt").write_text("x")

    from dycov.files.manage_files import check_output_dir

    with patch("builtins.input", return_value="y"):
        res = check_output_dir(d)

    assert res is False


def test_check_output_dir_no_overwrite(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    (d / "file.txt").write_text("x")

    from dycov.files.manage_files import check_output_dir

    with patch("builtins.input", return_value="n"):
        res = check_output_dir(d)

    assert res is True
