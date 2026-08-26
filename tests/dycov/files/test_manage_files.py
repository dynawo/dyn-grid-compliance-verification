#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the file management helpers (copy, versions, reports, curves)."""

import logging
import re
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from dycov.files.manage_files import (
    _copy_curve_files_by_name,
    check_output_dir,
    clone_as_subdirectory,
    copy_base_curves_files,
    copy_file,
    copy_from_path,
    create_config_file,
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

# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Basic file helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Read curves
# ---------------------------------------------------------------------------


def test_read_curves(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("time;value\n0;1\n1;2")

    df = read_curves(f)

    assert isinstance(df, pd.DataFrame)
    assert "time" in df.columns


# ---------------------------------------------------------------------------
# Curves copy
# ---------------------------------------------------------------------------


CANONICAL_NAME = "PCS_RTE-I2.USetPointStep.AReactance"


def _write_curve_pair(directory: Path, stem: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stem}.csv").write_text("time;P\n0;1\n")
    (directory / f"{stem}.dict").write_text("[Curves-Dictionary]\n")


def _write_curves_ini(directory: Path, mapping: str = "") -> None:
    directory.mkdir(parents=True, exist_ok=True)
    files_section = f"{CANONICAL_NAME} = {mapping}\n" if mapping else ""
    (directory / "CurvesFiles.ini").write_text(f"[Curves-Files]\n{files_section}")


def test_copy_curve_files_by_name(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curve_pair(src, "curve")

    res = _copy_curve_files_by_name(src, dst, "curve", "curve")

    assert len(res) == 2
    assert (dst / "curve.csv").exists()
    assert (dst / "curve.dict").exists()


def test_copy_curve_files_by_name_renames_to_target_stem(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curve_pair(src, "MyCurves")

    res = _copy_curve_files_by_name(src, dst, "MyCurves", CANONICAL_NAME)

    assert sorted(res) == [f"{CANONICAL_NAME}.csv", f"{CANONICAL_NAME}.dict"]
    assert (dst / f"{CANONICAL_NAME}.csv").exists()
    assert (dst / f"{CANONICAL_NAME}.dict").exists()


def test_copy_curve_files_by_name_missing_source(tmp_path):
    res = _copy_curve_files_by_name(tmp_path / "missing", tmp_path, "curve", "curve")

    assert res == []


def test_copy_curve_files_by_name_ignores_unsupported_extensions(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    src.mkdir()
    (src / "curve.txt").write_text("x")

    res = _copy_curve_files_by_name(src, dst, "curve", "curve")

    assert res == []


def test_copy_base_curves_files_fail(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    src.mkdir()
    dst.mkdir()

    res = copy_base_curves_files(src, dst, "test")

    assert res is False


def test_copy_base_curves_files_missing_source_dir(tmp_path):
    res = copy_base_curves_files(tmp_path / "missing", tmp_path, CANONICAL_NAME)

    assert res is False


def test_copy_base_curves_files_canonical_name(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curves_ini(src)
    _write_curve_pair(src, CANONICAL_NAME)

    res = copy_base_curves_files(src, dst, CANONICAL_NAME)

    assert res is True
    assert (dst / f"{CANONICAL_NAME}.csv").exists()
    assert (dst / f"{CANONICAL_NAME}.dict").exists()


def test_copy_base_curves_files_custom_relative_name(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curves_ini(src, "MyCurves.csv")
    _write_curve_pair(src, "MyCurves")

    res = copy_base_curves_files(src, dst, CANONICAL_NAME)

    assert res is True
    assert (dst / f"{CANONICAL_NAME}.csv").exists()
    assert (dst / f"{CANONICAL_NAME}.dict").exists()


def test_copy_base_curves_files_custom_subdirectory(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curves_ini(src, "sub/MyCurves.csv")
    _write_curve_pair(src / "sub", "MyCurves")

    res = copy_base_curves_files(src, dst, CANONICAL_NAME)

    assert res is True
    assert (dst / f"{CANONICAL_NAME}.csv").exists()
    assert (dst / f"{CANONICAL_NAME}.dict").exists()


def test_copy_base_curves_files_custom_absolute_path(tmp_path):
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    other = tmp_path / "other"
    dst.mkdir()
    _write_curves_ini(src, str(other / "MyCurves.csv"))
    _write_curve_pair(other, "MyCurves")

    res = copy_base_curves_files(src, dst, CANONICAL_NAME)

    assert res is True
    assert (dst / f"{CANONICAL_NAME}.csv").exists()
    assert (dst / f"{CANONICAL_NAME}.dict").exists()


def test_copy_base_curves_files_missing_dict(tmp_path, monkeypatch, caplog):
    _patch_dycov_logging(monkeypatch)
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curves_ini(src, "MyCurves.csv")
    src.mkdir(exist_ok=True)
    (src / "MyCurves.csv").write_text("time;P\n0;1\n")

    caplog.set_level(logging.WARNING)
    res = copy_base_curves_files(src, dst, CANONICAL_NAME)

    assert res is False
    assert any("'MyCurves.dict'" in record.message for record in caplog.records)


def _patch_dycov_logging(monkeypatch):
    monkeypatch.setattr(
        "dycov.logging.dycov_logging.get_logger",
        logging.getLogger,
        raising=True,
    )


def _write_curves_source(directory: Path, with_dict: bool = True, dict_stem: str = "curve"):
    directory.mkdir()
    (directory / "CurvesFiles.ini").write_text("[Curves-Files]\n")
    (directory / "curve.csv").write_text("time;P\n0;1\n")
    if with_dict:
        (directory / f"{dict_stem}.dict").write_text("[Curves-Dictionary]\n")


def test_copy_base_curves_files_warns_missing_dict(tmp_path, monkeypatch, caplog):
    _patch_dycov_logging(monkeypatch)
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curves_source(src, with_dict=False)

    caplog.set_level(logging.WARNING)
    res = copy_base_curves_files(src, dst, "curve")

    assert res is False
    assert any("'curve.dict'" in record.message for record in caplog.records)


def test_copy_base_curves_files_warns_misnamed_dict(tmp_path, monkeypatch, caplog):
    _patch_dycov_logging(monkeypatch)
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curves_source(src, dict_stem="other")

    caplog.set_level(logging.WARNING)
    res = copy_base_curves_files(src, dst, "curve")

    assert res is False
    assert any("'curve.dict'" in record.message for record in caplog.records)


def test_copy_base_curves_files_complete_set_without_warning(tmp_path, monkeypatch, caplog):
    _patch_dycov_logging(monkeypatch)
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    dst.mkdir()
    _write_curves_source(src)

    caplog.set_level(logging.WARNING)
    res = copy_base_curves_files(src, dst, "curve")

    assert res is True
    assert not any(".dict" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Config file
# ---------------------------------------------------------------------------


def test_create_config_file(tmp_path):
    src = tmp_path / "config.ini"
    dst = tmp_path / "out.ini"

    src.write_text("[section]\nvalue=1\nother=2\n")

    create_config_file(src, dst)

    content = dst.read_text()

    assert "[section]" in content
    assert "# other=2" in content


# ---------------------------------------------------------------------------
# Output dir
# ---------------------------------------------------------------------------


def test_check_output_dir_overwrite(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    (d / "file.txt").write_text("x")

    with patch("builtins.input", return_value="y"):
        res = check_output_dir(d)

    assert res is False


def test_check_output_dir_no_overwrite(tmp_path):
    d = tmp_path / "out"
    d.mkdir()
    (d / "file.txt").write_text("x")

    with patch("builtins.input", return_value="n"):
        res = check_output_dir(d)

    assert res is True
