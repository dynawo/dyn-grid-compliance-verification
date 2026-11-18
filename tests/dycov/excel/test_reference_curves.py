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

import pytest

from dycov.excel import names
from dycov.excel import reference_curves as rc
from dycov.excel import signals as sig
from dycov.excel.reference_curves import curves_files, dicts

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


# The metadata block: one column per key of a .dict's [Curves-Metadata] section.
METADATA_HEADERS = [
    "Mesures sur le terrain",
    "Début de l'événement",
    "durée du défaut",
    "échantillonnage fréquentiel",
]
METADATA_KEYS = [
    "is_field_measurements",
    "sim_t_event_start",
    "fault_duration",
    "frequency_sampling",
]


def _sheet(rows: list, tests: list, folder: str | None = "/curves") -> list:
    """A signal sheet: the signals table, the folder cell and the tests table.

    A test is ``(case, file)``, or ``(case, file, {metadata key: cell})`` to fill the metadata
    columns in as well.
    """
    grid = [["Signaux à fournir"], ["Grandeur", "Unité", "Variable associée dans les .csv"]]
    grid += [[label, "pu", column] for label, column in rows]
    grid += [[None], [None, None, None, None, None, None, "Dossier de résultats"]]
    grid += [[None, None, None, None, None, None, folder]]
    grid += [[None], [None, None, None, None, None, None, "Fichier de résultats .csv"]]
    grid += [["Cas", "Evènement à simuler", None, None, None, None, None] + METADATA_HEADERS]
    for test in tests:
        case, file = test[0], test[1]
        metadata = test[2] if len(test) > 2 else {}
        row = [case, "évènement", None, None, None, None, file]
        grid.append(row + [metadata.get(key) for key in METADATA_KEYS])
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
        "Wind_Turbine_GEN_ActivePowerSetpointPu": "PRef",
        "Wind_Turbine_GEN_ActiveCurrentNode2": "Ip2",
    }


def test_a_row_with_no_curve_of_its_own_is_informative_only():
    # The active power setpoint row of zone 3 is in the sheet because the DTR asks for it, but
    # DyCoV reads no such curve there, so it maps to nothing.
    rows = ZONE3_ROWS + [("Consigne de puissance active", "PRef")]

    parsed = sig.parse_zone_signals(_workbook(zone3=(rows, ZONE3_TESTS)), "Zone3", GEN)

    assert parsed.curves == {"BusPDR_BUS_Voltage": "U"}


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


def test_the_metadata_of_a_test_comes_from_its_own_row():
    filled = {
        "is_field_measurements": "Oui",
        "sim_t_event_start": "20.0",
        "fault_duration": "0.15",
        "frequency_sampling": "15",
    }
    parsed = sig.parse_zone_signals(
        _workbook(zone1=(ZONE1_ROWS, [("6", "scr3.csv", filled)])), "Zone1", GEN
    )

    # The boolean is translated to what DyCoV reads; the rest go as the workbook spells them.
    assert parsed.tests[0].metadata == {
        "is_field_measurements": "True",
        "sim_t_event_start": "20.0",
        "fault_duration": "0.15",
        "frequency_sampling": "15",
    }


def test_a_blank_metadata_cell_leaves_its_key_for_the_user():
    parsed = sig.parse_zone_signals(
        _workbook(zone1=(ZONE1_ROWS, [("6", "scr3.csv", {"fault_duration": "0.15"})])),
        "Zone1",
        GEN,
    )

    text = dicts.text(parsed, parsed.tests[0])

    assert "fault_duration = 0.15" in text
    assert "\nsim_t_event_start =\n" in text


def test_a_cell_that_does_not_mean_true_reads_as_false():
    parsed = sig.parse_zone_signals(
        _workbook(zone1=(ZONE1_ROWS, [("6", "scr3.csv", {"is_field_measurements": "Non"})])),
        "Zone1",
        GEN,
    )

    assert parsed.tests[0].metadata["is_field_measurements"] == "False"


def test_both_directions_of_a_storage_case_share_its_metadata():
    parsed = sig.parse_zone_signals(
        _workbook(zone1=(ZONE1_ROWS, [("6", "scr3.csv", {"sim_t_event_start": "20.0"})])),
        "Zone1",
        "Bess",
        storage=True,
    )

    assert [test.metadata["sim_t_event_start"] for test in parsed.tests] == ["20.0", "20.0"]


def test_an_absent_sheet_describes_nothing():
    parsed = sig.parse_zone_signals({}, "Zone3", GEN)

    assert (parsed.curves, parsed.tests, parsed.folder) == ({}, [], None)


def test_an_unfilled_sheet_describes_nothing():
    # Without a single .csv named, the sheet describes no test and the model inputs go on.
    parsed = sig.parse_zone_signals(_workbook(zone1=(ZONE1_ROWS, [("6", None)])), "Zone1", GEN)

    assert (parsed.curves, parsed.tests, parsed.folder) == ({}, [], None)


def test_the_generator_block_names_its_own_curves():
    parsed = sig.parse_zone_signals(_workbook(), "Zone1", "PV_Array")

    assert "PV_Array_GEN_ActiveCurrentNode2" in parsed.curves


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
    assert "Wind_Turbine_GEN_ActiveCurrentNode2 = Ip2" in text


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

    assert written == {
        "target": None,
        "tests": 0,
        "copied": 0,
        "missing": [],
        "unfilled": [],
        "without_row": [],
    }
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


# ---------------------------------------------------------------------------
# The tests of the revision of the DTR
# ---------------------------------------------------------------------------

_BOLTED = "PCS_RTE-I16z3.ThreePhaseFault.TransientBolted"
_IMPEDANT = "PCS_RTE-I16z3.ThreePhaseFault.TransientImpedant"
_QMIN = "PCS_RTE-I16z3.GridVoltageSwell.QMin"
_QMAX = "PCS_RTE-I16z3.GridVoltageSwell.QMax"
_QZERO = "PCS_RTE-I16z3.GridVoltageSwell.Qzero"

# The I5 and I7 rows of the template: the bolted and the impedant fault, and the swell at Qmin,
# Qmax and Q = 0.
_TEMPLATE_ROWS = [
    ("I5", "bolted.csv"),
    ("I5", "impedant.csv"),
    ("I7", "qmin.csv"),
    ("I7", "qmax.csv"),
    ("I7", "qzero.csv"),
]
# The rows of a workbook made on the template of the base revision.
_BASE_TEMPLATE_ROWS = [("I5", "bolted.csv"), ("I7", "qmin.csv"), ("I7", "qmax.csv")]


class _RevisionConfig:
    """The configuration, but for the revision of the DTR being validated."""

    def __init__(self, revision):
        self._revision = revision

    def get_value(self, section, key, default=None):
        if (section, key) == ("DTR", "current"):
            return self._revision
        return names_config.get_value(section, key, default)

    def get_config_dir(self):
        return names_config.get_config_dir()


names_config = names.config


@pytest.fixture
def revision(monkeypatch):
    def select(revision_name):
        monkeypatch.setattr(names, "config", _RevisionConfig(revision_name))

    return select


def _zone3_signals(rows: list, storage: bool = False) -> sig.ZoneSignals:
    workbook = {names.sheet("signals_zone3"): _sheet(ZONE3_ROWS, rows)}
    return sig.parse_zone_signals(workbook, "Zone3", GEN, storage=storage)


def _named(signals: sig.ZoneSignals) -> dict:
    return {test.name: test.curves_file for test in signals.tests}


def _fault_and_swell_without_row(names_without_row: list) -> list:
    """The tests of I5 and I7 among those without a row: the sheets of these tests have no other
    row."""
    return [name for name in names_without_row if ".ThreePhaseFault." in name or "Swell" in name]


@pytest.mark.parametrize("revision_name", ["20240215", "20250801", None])
def test_the_rows_of_the_base_template_run_the_tests_of_the_base(revision, revision_name):
    revision(revision_name)

    signals = _zone3_signals(_BASE_TEMPLATE_ROWS)

    assert _named(signals) == {_BOLTED: "bolted.csv", _QMIN: "qmin.csv", _QMAX: "qmax.csv"}
    assert _fault_and_swell_without_row(signals.without_row) == []


@pytest.mark.parametrize("revision_name", ["20251013", "20260723"])
def test_the_template_has_a_row_for_every_test_of_a_later_revision(revision, revision_name):
    revision(revision_name)

    signals = _zone3_signals(_TEMPLATE_ROWS)

    assert _named(signals) == {
        _BOLTED: "bolted.csv",
        _IMPEDANT: "impedant.csv",
        _QZERO: "qzero.csv",
    }
    assert _fault_and_swell_without_row(signals.without_row) == []


def test_the_template_runs_the_tests_of_the_base_under_the_base(revision):
    revision("20240215")

    signals = _zone3_signals(_TEMPLATE_ROWS)

    assert _named(signals) == {_BOLTED: "bolted.csv", _QMIN: "qmin.csv", _QMAX: "qmax.csv"}


def test_a_workbook_of_the_base_template_lacks_the_rows_a_later_revision_runs(revision):
    revision("20260723")

    signals = _zone3_signals(_BASE_TEMPLATE_ROWS)

    assert _named(signals) == {_BOLTED: "bolted.csv"}
    assert _fault_and_swell_without_row(signals.without_row) == [_IMPEDANT, _QZERO]


def test_a_storage_plant_lacks_both_tests_of_a_missing_row(revision):
    revision("20260723")

    signals = _zone3_signals(_BASE_TEMPLATE_ROWS, storage=True)

    assert _fault_and_swell_without_row(signals.without_row) == [
        f"{_IMPEDANT}Injection",
        f"{_IMPEDANT}Consumption",
        f"{_QZERO}Injection",
        f"{_QZERO}Consumption",
    ]


def test_a_row_marked_not_applicable_is_not_a_missing_row(revision):
    revision("20260723")
    rows = [
        (case, file if case != "I5" else names.marker("not_applicable"))
        for case, file in _TEMPLATE_ROWS
    ]

    signals = _zone3_signals(rows)

    assert _fault_and_swell_without_row(signals.without_row) == []
    assert _IMPEDANT not in _named(signals)


def test_the_tests_without_a_row_reach_the_report_of_the_reference_curves(tmp_path, revision):
    revision("20260723")

    written = rc.write_reference_curves(
        tmp_path, "Producer", {"Zone3": _zone3_signals(_BASE_TEMPLATE_ROWS)}
    )

    assert _fault_and_swell_without_row(written["without_row"]) == [_IMPEDANT, _QZERO]


def test_a_revision_section_of_the_user_copy_is_read_and_not_reported_as_unknown(
    tmp_path, revision, caplog
):
    user_copy = tmp_path / "excel_names.ini"
    user_copy.write_text(f"[Zone3-Tests.20250801]\nI7/3 = {_QZERO}\n")

    names._report_unknown(names._read(names.PACKAGE_NAMES_FILE), user_copy)

    assert "does not read" not in caplog.text
