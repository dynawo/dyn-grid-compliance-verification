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
    _copy_producer_tables,
    check_output_dir,
    clone_as_subdirectory,
    copy_base_curves_files,
    copy_file,
    copy_from_path,
    create_config_file,
    create_dir,
    discard_curves_set_aside,
    get_dynawo_version,
    get_latex_version,
    get_uv_version,
    has_curves,
    list_directories,
    move_report,
    read_curves,
    remove_dir,
    rename_path,
    set_curves_aside,
    should_copy,
    take_curves_back,
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


def test_create_dir_without_cleaning_keeps_what_the_directory_holds(tmp_path):
    d = tmp_path / "dir"
    d.mkdir()
    (d / "kept.txt").write_text("x")

    create_dir(d, clean_first=False)

    assert (d / "kept.txt").exists()


def test_create_dir_accepts_a_directory_created_after_it_looked(tmp_path, monkeypatch):
    d = tmp_path / "dir"
    d.mkdir()
    monkeypatch.setattr(Path, "exists", lambda path: False)

    create_dir(d)

    assert d.is_dir()


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


def test_copy_producer_tables(tmp_path):
    producer = tmp_path / "Zone1"
    producer.mkdir()
    (producer / "Producer.par").write_text("the par")
    (producer / "LHVRT.txt").write_text("the curves")
    (producer / "notes.md").write_text("not an input")
    target = tmp_path / "working"
    target.mkdir()

    _copy_producer_tables(producer, target)

    assert (target / "LHVRT.txt").read_text() == "the curves"
    assert sorted(p.name for p in target.iterdir()) == ["LHVRT.txt"]


def test_copy_producer_tables_lowercases_the_extension(tmp_path):
    producer = tmp_path / "Zone1"
    producer.mkdir()
    (producer / "LHVRT.TXT").write_text("the curves")
    target = tmp_path / "working"
    target.mkdir()

    _copy_producer_tables(producer, target)

    assert (target / "LHVRT.txt").read_text() == "the curves"


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


def test_a_test_has_curves_when_its_file_and_its_dictionary_are_there(tmp_path):
    _write_curves_ini(tmp_path)
    _write_curve_pair(tmp_path, CANONICAL_NAME)

    assert has_curves(tmp_path, CANONICAL_NAME) is True
    assert has_curves(tmp_path, "PCS_RTE-I2.USetPointStep.BReactance") is False


def test_a_test_has_the_curves_the_index_renames_for_it(tmp_path):
    _write_curves_ini(tmp_path, "records/measured.csv")
    _write_curve_pair(tmp_path / "records", "measured")

    assert has_curves(tmp_path, CANONICAL_NAME) is True


def test_a_curve_without_its_dictionary_is_no_curve(tmp_path):
    _write_curves_ini(tmp_path)
    (tmp_path / f"{CANONICAL_NAME}.csv").write_text("time;P\n0;1\n")

    assert has_curves(tmp_path, CANONICAL_NAME) is False


def test_a_directory_without_index_has_no_curves(tmp_path):
    _write_curve_pair(tmp_path, CANONICAL_NAME)

    assert has_curves(tmp_path, CANONICAL_NAME) is False


def _given_revision(monkeypatch, revision, base="20240215"):
    """Config is frozen, so the double replaces the method on the class."""
    from dycov.configuration.cfg import Config

    values = {
        ("Global", "templates_path"): "templates/PCS",
        ("DTR", "current"): revision,
        ("DTR", "base"): base,
    }
    monkeypatch.setattr(
        Config, "get_value", lambda self, section, key, default=None: values[(section, key)]
    )


def test_the_delta_of_a_revision_mirrors_the_templates(monkeypatch, tmp_path):
    from dycov.files import manage_files

    _given_revision(monkeypatch, "20250801")
    shipped = tmp_path / "templates" / "reports" / "PPM" / "PCS_RTE-I6"
    delta = tmp_path / "templates" / "revisions" / "20250801" / "reports" / "PPM" / "PCS_RTE-I6"
    delta.mkdir(parents=True)

    assert manage_files.dtr_delta_path(shipped) == delta


def test_a_revision_that_writes_no_delta_of_a_directory_has_none(monkeypatch, tmp_path):
    from dycov.files import manage_files

    _given_revision(monkeypatch, "20250801")

    assert (
        manage_files.dtr_delta_path(tmp_path / "templates" / "PCS" / "SM" / "PCS_RTE-I6") is None
    )


def test_a_path_outside_the_templates_has_no_delta(monkeypatch, tmp_path):
    from dycov.files import manage_files

    _given_revision(monkeypatch, "20250801")

    assert manage_files.dtr_delta_path(tmp_path / "model_lib" / "Omega") is None


def test_the_base_revision_has_no_delta_directory(monkeypatch, tmp_path):
    """The base is the catalogue itself, so nothing looks for a delta of it."""
    from dycov.files import manage_files

    _given_revision(monkeypatch, "20240215")
    delta = tmp_path / "templates" / "revisions" / "20240215" / "PCS" / "SM" / "PCS_RTE-I6"
    delta.mkdir(parents=True)

    assert (
        manage_files.dtr_delta_path(tmp_path / "templates" / "PCS" / "SM" / "PCS_RTE-I6") is None
    )


def _results_with_curves() -> dict:
    curves = pd.DataFrame({"time": [0.0, 0.001], "BusPDR_BUS_Voltage": [1.0, 0.99]})
    return {
        "compliance": True,
        "curves": curves,
        "reference_curves": curves * 2,
        "curves_error": {"before": 0.0},
    }


def test_the_curves_of_a_test_wait_on_disk_until_its_report_takes_them_back(tmp_path):
    results = _results_with_curves()

    set_aside = set_curves_aside(results, tmp_path)

    assert set(set_aside) == {"compliance", "curves_set_aside"}
    assert set_aside["curves_set_aside"].exists()

    taken_back = take_curves_back(set_aside)

    assert not set_aside["curves_set_aside"].exists()
    assert set(taken_back) == {"compliance", "curves", "reference_curves"}
    pd.testing.assert_frame_equal(taken_back["curves"], results["curves"])
    pd.testing.assert_frame_equal(taken_back["reference_curves"], results["reference_curves"])


def test_a_test_without_curves_keeps_its_results_as_they_are(tmp_path):
    failed = {"compliance": False, "curves": None}

    assert set_curves_aside(failed, tmp_path) is failed
    assert take_curves_back(failed) is failed
    assert not list(tmp_path.iterdir())


def test_the_curves_no_report_took_back_are_discarded(tmp_path):
    first, second = tmp_path / "Bench" / "OC1", tmp_path / "Bench" / "OC2"
    first.mkdir(parents=True)
    second.mkdir()
    take_curves_back(set_curves_aside(_results_with_curves(), first))
    set_curves_aside(_results_with_curves(), second)

    discard_curves_set_aside(tmp_path)

    assert not list(first.iterdir())
    assert not list(second.iterdir())
