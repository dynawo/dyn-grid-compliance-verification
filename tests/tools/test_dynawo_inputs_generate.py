#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the orchestration (``tools/dynawo_inputs/generate_inputs.py``).

The per-output modules are unit-tested next to them; here ``generate`` is exercised end to end
with the synthetic workbook from ``conftest`` (``read_workbook`` monkeypatched), writing a real
tree, plus the reports and the refusals."""

from __future__ import annotations

import configparser
from pathlib import Path

import generate_inputs as G
import par
import pytest
from lxml import etree
from workbooks import GENERAL, ZONE3_ROWS, make_workbook, variant_sheet


def test_submodel_report_lists_general_blocks_present_and_missing():
    resolved = {
        "zone3_lib": "PhotovoltaicsWeccCurrentSource",
        "zone3_prefix": "photovoltaics_",
        "zone1_lib": "PhotovoltaicsWeccCurrentSourceNoPlantControl",
        "zone1_prefix": "photovoltaics_",
    }
    # The reported blocks come from 'Général' (no fixed family list): an unknown block name is
    # reported all the same, and only blocks whose sheets contributed params are 'present'.
    selections = [("REPC", "REPC_A"), ("REEC", "REEC_B"), ("NEWBLK", "Aucun")]
    control = [
        {"block": "REPC", "name": "FreqFlag", "type": "BOOL", "value": "true", "comments": []},
        {"block": "REEC", "name": "Kqp", "type": "DOUBLE", "value": "1", "comments": []},
    ]

    report = G._submodel_report(resolved, selections, control)

    assert "REPC  : present" in report
    assert "NEWBLK : missing" in report
    assert "WTGT" not in report


def test_reference_curves_report_names_what_is_still_missing():
    report = G._reference_curves_report(
        {
            "target": Path("/out/ReferenceCurves/Producer"),
            "tests": 3,
            "copied": 2,
            "missing": ["rise.csv"],
        }
    )

    assert "tests described : 3" in report
    assert ".csv missing    : 1" in report and "rise.csv" in report


def test_reference_curves_report_says_when_the_sheets_describe_nothing():
    report = G._reference_curves_report({"target": None, "tests": 0, "copied": 0, "missing": []})

    assert "describe no test" in report


def test_control_params_are_filtered_by_the_zone_they_declare():
    control = [
        {"block": "REPC", "name": "FreqFlag", "type": "BOOL", "value": "true", "comments": []},
        {"block": "REEC", "name": "Kqp", "type": "DOUBLE", "value": "1", "comments": []},
        {"block": "NOZONE", "name": "X", "type": "DOUBLE", "value": "0", "comments": []},
    ]
    zones = {"REPC": ["Zone3"], "REEC": ["Zone1", "Zone3"]}  # NOZONE declares nothing

    z1 = par.control_params_for_zone(control, zones, "Zone1")
    z3 = par.control_params_for_zone(control, zones, "Zone3")

    assert [p["name"] for p in z1] == ["Kqp"]
    assert [p["name"] for p in z3] == ["FreqFlag", "Kqp"]  # a zone-less block enters neither
    assert all("block" not in p for p in z1 + z3)


def test_topology_spelled_with_spaces_is_accepted(tmp_path, monkeypatch):
    # The template's own legend spells it "S + Aux", while DyCoV matches the string exactly.
    book = make_workbook()
    book["Zone3"] = [
        ["cat", "Topologie", "d", "S + Aux + i", "u", "c"] if row[1:2] == ["Topologie"] else row
        for row in book["Zone3"]
    ]
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: book)

    G.generate(Path("ignored.xlsx"), tmp_path)

    cp = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cp.read(tmp_path / "Dynawo" / "Zone3" / "Producer.ini")
    assert cp.get("DEFAULT", "topology").strip() == "S+Aux+i"


def test_generate_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: make_workbook())

    report = G.generate(Path("ignored.xlsx"), tmp_path)

    root = tmp_path / "Dynawo"
    for zone in ("Zone1", "Zone3"):
        assert (root / zone / "Producer.dyd").exists()
        assert (root / zone / "Producer.par").exists()
        assert (root / zone / "Producer.ini").exists()

    # Zone3 DYD: concrete plant lib + terminal, no leftover placeholders
    dyd = (root / "Zone3" / "Producer.dyd").read_text()
    assert "PhotovoltaicsWeccCurrentSource" in dyd
    assert "photovoltaics_terminal" in dyd
    assert "photovoltaics_uPccPu_re" in dyd  # remote-control port filled from the same prefix
    assert "MODEL_PREFIX" not in dyd and "PPM_DYNAMIC_MODEL" not in dyd

    # Zone3 PAR: prefixed control param + main transformer taps + aux + line (topology S+Aux+i)
    par_root = etree.parse(str(root / "Zone3" / "Producer.par")).getroot()
    ns = etree.QName(par_root).namespace
    set_ids = [s.get("id") for s in par_root.iterfind(f"{{{ns}}}set")]
    assert G.dyd.GEN_ID_BY_TECH["PV"] in set_ids and "Main_Xfmr" in set_ids  # PV -> PV_Array
    assert "Aux_Load" in set_ids and "IntNetwork_Line" in set_ids
    names = [p.get("name") for p in par_root.iter(f"{{{ns}}}par")]
    assert "photovoltaics_Kqp" in names
    # Zone3's external transformer is the plant's main one: Z_cc_TP with its tap block, the group
    # transformer living inside the generator's model.
    main_xfmr = {
        p.get("name"): p.get("value")
        for s in par_root.iterfind(f"{{{ns}}}set")
        if s.get("id") == "Main_Xfmr"
        for p in s.iter(f"{{{ns}}}par")
    }
    assert main_xfmr["transformer_NbTap"] == "21" and main_xfmr["transformer_Tap0"] == "10"
    assert main_xfmr["transformer_XPu"] == "0.18"  # Z_cc_TP reactive, SnZone3 = 100 = SnRef
    assert "transformer_rTfoPu" not in main_xfmr
    # PAR order is documental: REPC precedes REEC precedes REGC because the sheets do.
    assert names.index("photovoltaics_FreqFlag") < names.index("photovoltaics_Kqp")
    assert names.index("photovoltaics_Kqp") < names.index("photovoltaics_Iqrmax")
    # Section comments and the Dynawo type mapping are preserved.
    par_text = (root / "Zone3" / "Producer.par").read_text()
    assert "<!-- REEC_B -->" in par_text
    assert 'type="BOOL"' in par_text and 'type="boolean"' not in par_text

    # Zone1 PAR: only the blocks declaring Zone1 — the plant control (Zone3-only) is excluded.
    z1_par = etree.parse(str(root / "Zone1" / "Producer.par")).getroot()
    z1_names = [p.get("name") for p in z1_par.iter(f"{{{ns}}}par")]
    assert "photovoltaics_Kqp" in z1_names
    assert "photovoltaics_FreqFlag" not in z1_names
    assert "photovoltaics_PPCLocal" in names
    assert "photovoltaics_PPCLocal" not in z1_names

    # Zone3 INI: filled values
    cp = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cp.read(root / "Zone3" / "Producer.ini")
    assert cp.get("DEFAULT", "u_nom_at_PDR").strip() == ZONE3_ROWS["Un_PDR"]
    assert cp.get("DEFAULT", "topology").strip() == "S+Aux+i"

    assert "present" in report


def test_generate_writes_no_reference_curves_when_the_workbook_has_no_signal_sheet(
    tmp_path, monkeypatch
):
    # The signal sheets are optional: their absence must not stop the model inputs.
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: make_workbook())

    report = G.generate(Path("ignored.xlsx"), tmp_path)

    assert not (tmp_path / "ReferenceCurves").exists()
    assert "describe no test" in report


def test_generate_fails_when_no_block_declares_zone1(tmp_path, monkeypatch):
    # Fail safe: with no 'Zone' column at all (or none declaring Zone1), Zone1 would come out
    # silently incomplete — the tool must refuse instead.
    book = make_workbook()
    book["Général"] = [row[:2] + row[3:] for row in GENERAL]  # strip only the Zone column
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: book)

    with pytest.raises(ValueError, match="declares Zone1"):
        G.generate(Path("ignored.xlsx"), tmp_path)


def test_main_reports_domain_errors_cleanly(tmp_path, monkeypatch, capsys):
    # Domain errors exit 1 with an 'ERROR: …' line on stderr (like dynawo_par), no traceback.
    book = make_workbook()
    book["Général"] = [row[:2] + row[3:] for row in GENERAL]  # no Zone column -> ValueError
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: book)
    excel = tmp_path / "model.xlsx"
    excel.write_text("stub")

    assert G.main(["--excel", str(excel), "--outdir", str(tmp_path / "out")]) == 1

    err = capsys.readouterr().err
    assert err.startswith("ERROR: ") and "declares Zone1" in err


def test_generate_fails_when_zone1_blocks_have_no_values(tmp_path, monkeypatch):
    # An unfilled template: the Zone1 blocks exist and declare their zone, but every value
    # cell is empty — the error must say so instead of blaming the 'Zone' column.
    book = make_workbook()
    book["REEC"] = variant_sheet("REEC_B", [("Kqp", "double", None)])
    book["REGC"] = variant_sheet("REGC_A", [("Iqrmax", "double", None)])
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: book)

    with pytest.raises(
        ValueError, match=r"Zone1 control blocks \(REEC, REGC\) carry no parameter values"
    ):
        G.generate(Path("ignored.xlsx"), tmp_path)
