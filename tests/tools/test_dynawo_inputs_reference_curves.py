#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the reference-curve inputs: the signal sheets (``signals.py``) and the files they
produce (``reference_curves/``)."""

from __future__ import annotations

import pytest
import reference_curves as rc
import signals as sig
from reference_curves import curves_files, dicts

_SIGNALS_HEADER = ["Grandeur", "Unité", "Variable associée dans les .csv", "Nom DyCoV"]
_TESTS_HEADER = [
    None,
    None,
    None,
    None,
    None,
    None,
    "Fichier de résultats .csv",
    None,
    "Test DyCoV",
]


FOLDER_LABEL = "Dossier de résultats pour les courbes de références"


def _sheet(curves: list, tests: list, folder: str | None = "/curves") -> list:
    """A signal sheet: the signals table, the folder cell and the tests table."""
    grid = [["title"], _SIGNALS_HEADER]
    grid += [[label, "pu", column, name] for label, name, column in curves]
    grid += [
        [None],
        [
            "Dossier de résultats pour les courbes de références",
            None,
            None,
            None,
            None,
            None,
            None,
        ],
    ]
    grid += [[folder]] if folder else [[None]]
    grid += [[None], list(_TESTS_HEADER)]
    for name, file in tests:
        row = [None] * 9
        row[6], row[8] = file, name
        grid.append(row)
    return grid


def _workbook(
    zone1_curves, zone1_tests, zone3_curves=(), zone3_tests=(), folder="/curves"
) -> dict:
    return {
        sig.SHEETS["Zone1"]: _sheet(list(zone1_curves), list(zone1_tests), folder),
        sig.SHEETS["Zone3"]: _sheet(list(zone3_curves), list(zone3_tests), folder),
    }


ZONE1_CURVES = [
    ("Tension au nœud 1", "InternalNode1_BUS_Voltage", "U1"),
    ("Courant actif au nœud 1", "InternalNode1_BUS_ActiveCurrent", "Ip1"),
]
ZONE1_TESTS = [("PCS_RTE-I16z1.SetPointStep.Active", "step_active.csv")]


def test_parse_zone_signals_reads_curves_tests_and_folder():
    book = _workbook(ZONE1_CURVES, ZONE1_TESTS)

    parsed = sig.parse_zone_signals(book, "Zone1")

    assert parsed.curves == {
        "InternalNode1_BUS_Voltage": "U1",
        "InternalNode1_BUS_ActiveCurrent": "Ip1",
    }
    assert [(t.name, t.curves_file) for t in parsed.tests] == [
        ("PCS_RTE-I16z1.SetPointStep.Active", "step_active.csv")
    ]
    assert parsed.folder.startswith("/curves")


def test_a_row_the_user_left_unfilled_is_not_mapped():
    book = _workbook(
        ZONE1_CURVES + [("Fréquence", "NetworkFrequencyPu", None)],
        ZONE1_TESTS + [("PCS_RTE-I16z1.SetPointStep.Voltage", "/")],
    )

    parsed = sig.parse_zone_signals(book, "Zone1")

    assert "NetworkFrequencyPu" not in parsed.curves
    assert [t.name for t in parsed.tests] == ["PCS_RTE-I16z1.SetPointStep.Active"]


def test_an_absent_sheet_describes_nothing():
    parsed = sig.parse_zone_signals({}, "Zone3")

    assert (parsed.curves, parsed.tests, parsed.folder) == ({}, [], None)


def test_the_signals_table_needs_the_dycov_name_column():
    book = _workbook(ZONE1_CURVES, ZONE1_TESTS)
    book[sig.SHEETS["Zone1"]][1] = _SIGNALS_HEADER[:3]  # drop the 'Nom DyCoV' header

    with pytest.raises(ValueError, match="signals table needs a 'nom dycov' column"):
        sig.parse_zone_signals(book, "Zone1")


def test_a_sheet_with_no_tests_table_describes_nothing():
    # An untouched sheet must not stop the model inputs: it simply describes no test.
    book = _workbook(ZONE1_CURVES, ZONE1_TESTS)
    grid = book[sig.SHEETS["Zone1"]]
    grid[-2] = [c if c != "Test DyCoV" else None for c in grid[-2]]

    parsed = sig.parse_zone_signals(book, "Zone1")

    assert (parsed.curves, parsed.tests, parsed.folder) == ({}, [], None)


def test_curves_files_text_lists_every_test_and_one_dictionary_per_zone():
    parsed = sig.parse_signals(
        _workbook(
            ZONE1_CURVES,
            ZONE1_TESTS,
            [("Tension au PDR", "BusPDR_BUS_Voltage", "U")],
            [("PCS_RTE-I16z3.PSetPointStep.Inc40", "p_inc40.csv")],
        )
    )

    text = curves_files.text(parsed)

    assert "PCS_RTE-I16z1.SetPointStep.Active = step_active.csv" in text
    assert "PCS_RTE-I16z3.PSetPointStep.Inc40 = p_inc40.csv" in text
    assert "[Curves-Dictionary-Zone1]" in text and "[Curves-Dictionary-Zone3]" in text
    assert "InternalNode1_BUS_Voltage = U1" in text
    assert "time = time" in text


def test_dict_text_leaves_the_metadata_for_the_user():
    parsed = sig.parse_zone_signals(_workbook(ZONE1_CURVES, ZONE1_TESTS), "Zone1")

    text = dicts.text(parsed)

    for key in dicts.METADATA_HELP:
        assert "\n%s =\n" % key in text  # the key is there, the value is the user's
    assert "InternalNode1_BUS_ActiveCurrent = Ip1" in text
    assert "MaxInjectedCurrentPu" in text  # the optional per-generator key is documented


def test_write_reference_curves_copies_the_files_it_finds(tmp_path):
    folder = tmp_path / "curves"
    folder.mkdir()
    (folder / "step_active.csv").write_text("time\n0\n", encoding="utf-8")
    book = _workbook(
        ZONE1_CURVES,
        ZONE1_TESTS + [("PCS_RTE-I16z1.GridVoltageStep.Rise", "rise.csv")],
        folder=str(folder),
    )

    written = rc.write_reference_curves(tmp_path / "out", "Producer", sig.parse_signals(book))

    target = tmp_path / "out" / "ReferenceCurves" / "Producer"
    assert written["target"] == target
    assert written["tests"] == 2
    assert (written["copied"], written["missing"]) == (1, ["rise.csv"])
    assert (target / "CurvesFiles.ini").is_file()
    assert (target / "PCS_RTE-I16z1.SetPointStep.Active.dict").is_file()
    assert (target / "step_active.csv").is_file()


def test_write_reference_curves_writes_nothing_when_no_test_is_described(tmp_path):
    written = rc.write_reference_curves(tmp_path, "Producer", sig.parse_signals({}))

    assert written == {"target": None, "tests": 0, "copied": 0, "missing": []}
    assert not (tmp_path / "ReferenceCurves").exists()
