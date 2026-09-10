#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#

"""Tests for the reference-curve inputs: the signal sheets (``signals.py``), the names that give
them meaning (``excel_names.ini``) and the files they produce (``reference_curves/``)."""

from __future__ import annotations

import excel_names as names
import pytest
import reference_curves as rc
import signals as sig
from reference_curves import curves_files, dicts

GEN = "Wind_Turbine"

# Rows as the sheets spell them: the label, the unit, and the column the user fills in.
ZONE1_ROWS = [
    ("Tension directe (RMS) au nœud 1", "U1"),
    ("Consigne de puissance active envoyée au convertisseur", "PRef"),
    ("Courant actif direct injecté au nœud 2", "Ip2"),
]
ZONE1_TESTS = [("6", "bolted_scr3.csv"), ("14", "freq_ramp.csv")]
ZONE3_ROWS = [("Tension directe au PDR", "U")]
ZONE3_TESTS = [("I2", "u_step_a.csv"), ("I2", "u_step_b.csv")]


def _sheet(rows: list, tests: list, folder: str | None = "/curves") -> list:
    """A signal sheet: the signals table, the folder cell and the tests table."""
    grid = [["Signaux à fournir"], ["Grandeur", "Unité", "Variable associée dans les .csv"]]
    grid += [[label, "pu", column] for label, column in rows]
    grid += [[None], [None, None, None, None, None, None, "Dossier de résultats"]]
    grid += [[None, None, None, None, None, None, folder]]
    grid += [[None], [None, None, None, None, None, None, "Fichier de résultats .csv"]]
    grid += [["Cas", "Evènement à simuler"]]
    grid += [[case, "évènement", None, None, None, None, file] for case, file in tests]
    return grid


def _workbook(zone1=(ZONE1_ROWS, ZONE1_TESTS), zone3=(ZONE3_ROWS, ZONE3_TESTS), folder="/curves"):
    return {
        names.sheet("signals_zone1"): _sheet(list(zone1[0]), list(zone1[1]), folder),
        names.sheet("signals_zone3"): _sheet(list(zone3[0]), list(zone3[1]), folder),
    }


def test_a_row_is_mapped_to_the_curve_its_label_stands_for():
    parsed = sig.parse_zone_signals(_workbook(), "Zone1", GEN)

    # The label decides the curve, and the sheet only carries the column that holds it.
    assert parsed.curves == {
        "InternalNode1_BUS_Voltage": "U1",
        "Wind_Turbine_GEN_IpInjTerminal": "Ip2",
    }


def test_a_row_with_no_curve_of_its_own_is_informative_only():
    # The setpoint rows are in the sheet because the DTR asks for them, but DyCoV reads no such
    # curve, so they map to nothing.
    parsed = sig.parse_zone_signals(_workbook(), "Zone1", GEN)

    assert not any("Setpoint" in curve for curve in parsed.curves)


def test_a_case_is_mapped_to_the_operating_condition_it_runs_as():
    parsed = sig.parse_zone_signals(_workbook(), "Zone1", GEN)

    # Case 6 is a DyCoV test; case 14 (the frequency ramp) does not apply to Zone 1.
    assert [(t.name, t.curves_file) for t in parsed.tests] == [
        ("PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3", "bolted_scr3.csv")
    ]


def test_repeated_sheets_are_told_apart_by_their_position():
    # A DTR sheet covers several operating conditions: the first I2 row is the A reactance, the
    # second the B one.
    parsed = sig.parse_zone_signals(_workbook(), "Zone3", GEN)

    assert [t.name for t in parsed.tests] == [
        "PCS_RTE-I16z3.USetPointStep.AReactance",
        "PCS_RTE-I16z3.USetPointStep.BReactance",
    ]


def test_a_test_whose_file_is_not_given_is_left_out():
    parsed = sig.parse_zone_signals(
        _workbook(zone1=(ZONE1_ROWS, [("6", None), ("7", "scr10.csv")])), "Zone1", GEN
    )

    assert [t.curves_file for t in parsed.tests] == ["scr10.csv"]


def test_a_storage_case_describes_one_test_per_direction():
    # A storage plant runs every case injecting and consuming, so the workbook carries the base
    # name of the .csv files and each suffix names one test and one file.
    parsed = sig.parse_zone_signals(
        _workbook(zone1=(ZONE1_ROWS, [("6", "bolted_scr3.csv")])), "Zone1", "Bess", storage=True
    )

    assert [(test.name, test.curves_file) for test in parsed.tests] == [
        (
            "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Injection",
            "bolted_scr3Injection.csv",
        ),
        (
            "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3Consumption",
            "bolted_scr3Consumption.csv",
        ),
    ]


def test_a_plant_that_is_not_storage_describes_one_test_per_case():
    parsed = sig.parse_zone_signals(
        _workbook(zone1=(ZONE1_ROWS, [("6", "bolted_scr3.csv")])), "Zone1", GEN
    )

    assert [test.name for test in parsed.tests] == [
        "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3"
    ]


def test_storage_writes_the_two_files_of_every_case(tmp_path):
    folder = tmp_path / "curves"
    folder.mkdir()
    (folder / "scr3Injection.csv").write_text("time\n0\n", encoding="utf-8")
    book = _workbook(
        zone1=(ZONE1_ROWS, [("6", "scr3.csv")]), zone3=(ZONE3_ROWS, []), folder=str(folder)
    )

    written = rc.write_reference_curves(
        tmp_path / "out", "Producer", sig.parse_signals(book, "Bess", storage=True)
    )

    target = tmp_path / "out" / "ReferenceCurves" / "Producer"
    assert written["tests"] == 2
    assert (written["copied"], written["missing"]) == (1, ["scr3Consumption.csv"])
    for suffix in names.test_suffixes():
        name = "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3%s.dict" % suffix
        assert (target / name).is_file()


def test_an_absent_sheet_describes_nothing():
    parsed = sig.parse_zone_signals({}, "Zone3", GEN)

    assert (parsed.curves, parsed.tests, parsed.folder) == ({}, [], None)


def test_an_unfilled_sheet_describes_nothing():
    # Without a single .csv named, the sheet describes no test and the model inputs go on.
    parsed = sig.parse_zone_signals(_workbook(zone1=(ZONE1_ROWS, [("6", None)])), "Zone1", GEN)

    assert (parsed.curves, parsed.tests, parsed.folder) == ({}, [], None)


def test_the_generator_block_names_its_own_curves():
    parsed = sig.parse_zone_signals(_workbook(), "Zone1", "PV_Array")

    assert "PV_Array_GEN_IpInjTerminal" in parsed.curves


def test_curves_files_text_lists_every_test_and_one_dictionary_per_zone():
    parsed = sig.parse_signals(_workbook(), GEN)

    text = curves_files.text(parsed)

    assert "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3 = bolted_scr3.csv" in text
    assert "PCS_RTE-I16z3.USetPointStep.BReactance = u_step_b.csv" in text
    assert "[Curves-Dictionary-Zone1]" in text and "[Curves-Dictionary-Zone3]" in text
    assert "InternalNode1_BUS_Voltage = U1" in text
    assert "time = time" in text


def test_dict_text_leaves_the_metadata_for_the_user():
    parsed = sig.parse_zone_signals(_workbook(), "Zone1", GEN)

    text = dicts.text(parsed)

    for key in dicts.METADATA_HELP:
        assert "\n%s =\n" % key in text  # the key is there, the value is the user's
    assert "Wind_Turbine_GEN_IpInjTerminal = Ip2" in text


def test_write_reference_curves_copies_the_files_it_finds(tmp_path):
    folder = tmp_path / "curves"
    folder.mkdir()
    (folder / "bolted_scr3.csv").write_text("time\n0\n", encoding="utf-8")
    book = _workbook(
        zone1=(ZONE1_ROWS, [("6", "bolted_scr3.csv"), ("7", "scr10.csv")]),
        zone3=(ZONE3_ROWS, []),
        folder=str(folder),
    )

    written = rc.write_reference_curves(tmp_path / "out", "Producer", sig.parse_signals(book, GEN))

    target = tmp_path / "out" / "ReferenceCurves" / "Producer"
    assert written["target"] == target
    assert written["tests"] == 2
    assert (written["copied"], written["missing"]) == (1, ["scr10.csv"])
    assert (target / "CurvesFiles.ini").is_file()
    assert (target / "PCS_RTE-I16z1.ThreePhaseFault.TransientBoltedSCR3.dict").is_file()
    assert (target / "bolted_scr3.csv").is_file()


def test_write_reference_curves_writes_nothing_when_no_test_is_described(tmp_path):
    written = rc.write_reference_curves(tmp_path, "Producer", sig.parse_signals({}, GEN))

    assert written == {"target": None, "tests": 0, "copied": 0, "missing": []}
    assert not (tmp_path / "ReferenceCurves").exists()


def test_every_curve_of_the_names_file_is_a_dycov_curve():
    # The mapping is data: guard it against a typo that would silently drop a curve.
    for zone, expected in (("Zone1", 8), ("Zone3", 9)):
        curves = names.curves(zone, GEN)

        assert len(curves) == expected
        assert all("{gen}" not in curve for curve in curves.values())


def test_a_missing_name_says_where_to_define_it():
    with pytest.raises(ValueError, match="not defined under .Sheets. in excel_names.ini"):
        names.sheet("zone2")
