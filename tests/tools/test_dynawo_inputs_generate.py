# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Tests for the Excel -> DyCoV orchestration/emission (``tools/dynawo_inputs/generate_inputs.py``).

Pure PAR-set builders are unit-tested with synthetic dicts; ``generate`` is smoke-tested
end-to-end with a hand-built workbook (``read_workbook`` monkeypatched), writing a real tree."""

from __future__ import annotations

import configparser
import sys
from pathlib import Path

import pytest
from lxml import etree

_TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "dynawo_inputs"
sys.path.insert(0, str(_TOOL_DIR))

import generate_inputs as G  # noqa: E402

ZONE1 = {
    "SnZone1": "100", "Z_cc_TG": "0.1", "R_cc_TG / X_cc_TG": "0", "ConverterLVControl": "True",
    "Z_cc_LvTr": "0.0001", "R_cc_LvTr / X_cc_LvTr": "0",
    "r_TG": "1", "Un1": "33", "Un2": "0.7", "Pmax_injection_z1": "1", "Pmax_soutirage_z1": "0",
    "Qmax_z1": "0.4", "Qmin_z1": "-0.4", "P_share": "1", "Q_share": "1",
}
ZONE3 = {
    "SnZone3": "100", "Topologie": "S+Aux+i", "Un_PDR": "63", "Pmax_PDR": "90", "Qmax_PDR": "30",
    "Qmin_PDR": "-30", "Z_cc_TP": "0.18", "R_cc_TP / X_cc_TP": "0", "N_prises": "20",
    "r_min": "0.9", "r_max": "1.1", "Un1": "33",
    "Sn_A": "2", "r_TA": "1", "Z_cc_TA": "0.1", "R_cc_TA / X_cc_TA": "0", "P_A": "1", "Q_A": "0.5",
    "alpha": "1.5", "beta": "2.5", "R_rc": "0.2", "X_rc": "1", "B_rc": "0", "G_rc": "0",
}


def _named(params):
    return {p["name"]: p["value"] for p in params}


def test_converter_par_set_prefix_control_snom():
    control = [{"name": "Kqp", "type": "DOUBLE", "value": "1"}]
    par_id, params = G.converter_par_set("PV_Array", "photovoltaics_", control, ZONE1, "100")
    named = _named(params)
    assert par_id == "PV_Array"
    assert named["photovoltaics_Kqp"] == "1"  # control param, prefixed, value verbatim
    assert named["photovoltaics_ConverterLVControl"] == "true"
    assert named["photovoltaics_SNom"] == pytest.approx(100.0)
    # The internal LvTr is always emitted, from Z_cc_LvTr (0.0001 on base SnZone1=100), separate
    # from the external StepUp_Xfmr (which carries Z_cc_TG).
    assert named["photovoltaics_XLvTrPu"] == pytest.approx(0.0001)
    assert named["photovoltaics_RLvTrPu"] == pytest.approx(0.0)


def test_converter_par_set_lvtr_from_its_own_field_regardless_of_lv_control():
    # The LvTr comes from Z_cc_LvTr, not Z_cc_TG, and is emitted whatever ConverterLVControl is.
    zone1_false = {**ZONE1, "ConverterLVControl": "False", "Z_cc_LvTr": "0.05"}
    _id, params = G.converter_par_set("PV_Array", "photovoltaics_", [], zone1_false, "100")
    named = _named(params)
    assert named["photovoltaics_ConverterLVControl"] == "false"
    assert named["photovoltaics_XLvTrPu"] == pytest.approx(0.05)  # Z_cc_LvTr on base SnZone1=100
    assert named["photovoltaics_RLvTrPu"] == pytest.approx(0.0)


def test_main_transformer_par_set():
    par_id, params = G.main_transformer_par_set("StepUp_Xfmr", ZONE3)
    named = _named(params)
    assert named["transformer_XPu"] == pytest.approx(0.18)
    assert named["transformer_RPu"] == pytest.approx(0.0)
    assert named["transformer_SNom"] == pytest.approx(100.0)
    assert named["transformer_NbTap"] == 21
    assert named["transformer_Tap0"] == 10
    assert named["transformer_RatioTfoMinPu"] == pytest.approx(0.9)


def test_group_transformer_par_set_fixed_ratio():
    # Z_cc_TG=0.1 on base SnZone1=100 -> XPu=0.1; from Zone1a in both zones (base = s_nom).
    _par_id, params = G.group_transformer_par_set("StepUp_Xfmr", ZONE1, ZONE1["SnZone1"])
    named = _named(params)
    assert named["transformer_XPu"] == pytest.approx(0.1)
    assert named["transformer_rTfoPu"] == pytest.approx(1.0)
    assert "transformer_NbTap" not in named  # fixed ratio -> no taps


def test_aux_load_and_line_par_sets():
    _p, load = G.aux_load_par_set("Aux_Load", ZONE3)
    named = _named(load)
    assert named["load_PRefPu"] == pytest.approx(0.01)  # P_A=1 MW / 100
    assert named["load_QRefPu"] == pytest.approx(0.005)
    assert named["load_alpha"] == pytest.approx(1.5)

    _p2, line = G.collector_line_par_set("IntNetwork_Line", ZONE3)
    z_base = 33.0**2 / 100.0
    assert _named(line)["line_XPu"] == pytest.approx(1.0 / z_base)


def test_drop_group_transformer_when_no_lv_control(tmp_path):
    # ConverterLVControl=False: no gen transformer -> StepUp_Xfmr removed, gen wired downstream.
    from dycov.files.producer_dyd_file import create_producer_dyd_file

    (tmp_path / "Zone1").mkdir()
    (tmp_path / "Zone3").mkdir()
    create_producer_dyd_file(tmp_path, "S", "model_PPM")
    dyd = tmp_path / "Zone1" / "Producer.dyd"
    gen = "Wind_Turbine"  # builder's S gen id
    G.drop_group_transformer(dyd, gen, "photovoltaics_terminal")

    root = etree.parse(str(dyd)).getroot()
    ns = etree.QName(root).namespace
    ids = [b.get("id") for b in root.iterfind(f"{{{ns}}}blackBoxModel")]
    assert "StepUp_Xfmr" not in ids
    conns = [
        (c.get("id1"), c.get("var1"), c.get("id2"), c.get("var2"))
        for c in root.iterfind(f"{{{ns}}}connect")
    ]
    assert not any("StepUp_Xfmr" in (c[0], c[2]) for c in conns)
    # generator now connects directly to what the transformer fed (BusPDR in S)
    assert (gen, "photovoltaics_terminal", "BusPDR", "bus_terminal") in conns


def test_submodel_report_lists_general_blocks_present_and_missing():
    resolved = {
        "zone3_lib": "PhotovoltaicsWeccCurrentSource", "zone3_prefix": "photovoltaics_",
        "zone1_lib": "PhotovoltaicsWeccCurrentSourceNoPlantControl", "zone1_prefix": "photovoltaics_",
    }
    # The reported blocks come from 'Général' (no fixed family list): an unknown block name is
    # reported all the same, and only blocks whose sheets contributed params are 'present'.
    selections = [("REPC", "REPC_A"), ("REEC", "REEC_B"), ("NEWBLK", "Aucun")]
    control = [
        {"block": "REPC", "name": "FreqFlag", "type": "BOOL", "value": "true", "comments": []},
        {"block": "REEC", "name": "Kqp", "type": "DOUBLE", "value": "1", "comments": []},
    ]
    report = G.submodel_report(resolved, selections, control)
    assert "REPC  : present" in report
    assert "NEWBLK : missing" in report
    assert "WTGT" not in report


def test_zone_control_params_filters_by_declared_zone_and_drops_label():
    control = [
        {"block": "REPC", "name": "FreqFlag", "type": "BOOL", "value": "true", "comments": []},
        {"block": "REEC", "name": "Kqp", "type": "DOUBLE", "value": "1", "comments": []},
        {"block": "NOZONE", "name": "X", "type": "DOUBLE", "value": "0", "comments": []},
    ]
    zones = {"REPC": ["Zone3"], "REEC": ["Zone1", "Zone3"]}  # NOZONE declares nothing
    z1 = G.zone_control_params(control, zones, "Zone1")
    z3 = G.zone_control_params(control, zones, "Zone3")
    assert [p["name"] for p in z1] == ["Kqp"]
    assert [p["name"] for p in z3] == ["FreqFlag", "Kqp"]  # a zone-less block enters neither
    assert all("block" not in p for p in z1 + z3)


# ---------------------------------------------------------------------------
# End-to-end smoke test (synthetic workbook)
# ---------------------------------------------------------------------------

_GENERAL = [
    ["Type de bloc", "Choix", "Zone", None, "Combinaison sélectionnée (clé Model Map)",
     "Zone3 lib", "Zone3 prefix", "Zone1 lib", "Zone1 prefix"],
    ["REPC", "REPC_A", "Zone3", None, "REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun"],
    ["REEC", "REEC_B", "Zone1;Zone3"], ["REGC", "REGC_A", "Zone1;Zone3"],
    ["WTGT", "Aucun", "Zone1;Zone3"], ["WTGP", "Aucun", "Zone1;Zone3"],
    ["WTGA", "Aucun", "Zone1;Zone3"], ["WTGQ", "Aucun", "Zone1;Zone3"],
]
_MODEL_MAP = [
    ["Key", "Zone3_lib", "Zone3_prefix", "Zone1_lib", "Zone1_prefix"],
    ["REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun", "PhotovoltaicsWeccCurrentSource", "photovoltaics_",
     "PhotovoltaicsWeccCurrentSourceNoPlantControl", "photovoltaics_"],
]
def _variant_sheet(variant_name, params):
    """A control-param sheet: variant name sits on the row above the 'Parameter' header."""
    grid = [[variant_name], ["Parameter", "Type", "Value"]]
    grid += [[name, typ, val] for name, typ, val in params]
    return grid


# Every selected non-Aucun block needs its variant table (else _selected_variants raises).
_REPC = _variant_sheet("REPC_A", [("FreqFlag", "boolean", "true")])
_REEC = _variant_sheet("REEC_B", [("Kqp", "double", "1.0"), ("QFlag", "boolean", "true")])
_REGC = _variant_sheet("REGC_A", [("Iqrmax", "double", "20")])


def _make_workbook():
    zone1_grid = [["intro"], ["Paramètres", "Descriptions", "Valeurs", "Unités", "Commentaires"]]
    zone1_grid += [[k, "d", v, "u", "c"] for k, v in ZONE1.items()]
    zone3_grid = [["defs"], ["Catégorie", "Paramètres", "Descriptions", "Valeurs", "Unités", "Cmt"]]
    zone3_grid += [["cat", k, "d", v, "u", "c"] for k, v in ZONE3.items()]
    return {
        "Général": _GENERAL,
        "Model Map": _MODEL_MAP,
        "Zone1a": zone1_grid,
        "Zone3": zone3_grid,
        "REPC": _REPC,
        "REEC": _REEC,
        "REGC": _REGC,
    }


def test_generate_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: _make_workbook())
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
    assert "MODEL_PREFIX" not in dyd and "PPM_DYNAMIC_MODEL" not in dyd  # no leftover placeholders

    # Zone3 PAR: prefixed control param + main transformer taps + aux + line (topology S+Aux+i)
    par = etree.parse(str(root / "Zone3" / "Producer.par")).getroot()
    ns = etree.QName(par).namespace
    set_ids = [s.get("id") for s in par.iterfind(f"{{{ns}}}set")]
    assert G.GEN_ID_BY_TECH["PV"] in set_ids and "StepUp_Xfmr" in set_ids  # PV -> PV_Array
    assert "Aux_Load" in set_ids and "IntNetwork_Line" in set_ids
    names = [p.get("name") for p in par.iter(f"{{{ns}}}par")]
    assert "photovoltaics_Kqp" in names
    # PAR order is documental: REPC precedes REEC precedes REGC because the sheets do.
    assert names.index("photovoltaics_FreqFlag") < names.index("photovoltaics_Kqp")
    assert names.index("photovoltaics_Kqp") < names.index("photovoltaics_Iqrmax")
    # Excel-derived section comments (design 8.3) and the Dynawo type mapping are preserved.
    par_text = (root / "Zone3" / "Producer.par").read_text()
    assert "<!-- REEC -->" in par_text
    assert 'type="BOOL"' in par_text and 'type="boolean"' not in par_text

    # Zone1 PAR: only the blocks declaring Zone1 — the plant control (Zone3-only) is excluded.
    z1_par = etree.parse(str(root / "Zone1" / "Producer.par")).getroot()
    z1_names = [p.get("name") for p in z1_par.iter(f"{{{ns}}}par")]
    assert "photovoltaics_Kqp" in z1_names
    assert "photovoltaics_FreqFlag" not in z1_names

    # Zone3 INI: filled values
    cp = configparser.ConfigParser(inline_comment_prefixes=("#",))
    cp.read(root / "Zone3" / "Producer.ini")
    assert cp.get("DEFAULT", "u_nom_at_PDR").strip() == "63"
    assert cp.get("DEFAULT", "topology").strip() == "S+Aux+i"

    assert "present" in report


def test_generate_fails_when_no_block_declares_zone1(tmp_path, monkeypatch):
    # Fail safe: with no 'Zone' column at all (or none declaring Zone1), Zone1 would come out
    # silently incomplete — the tool must refuse instead.
    book = _make_workbook()
    book["Général"] = [row[:2] + row[3:] for row in _GENERAL]  # strip only the Zone column
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: book)
    with pytest.raises(ValueError, match="declares Zone1"):
        G.generate(Path("ignored.xlsx"), tmp_path)


def test_main_reports_domain_errors_cleanly(tmp_path, monkeypatch, capsys):
    # Domain errors exit 1 with an 'ERROR: …' line on stderr (like dynawo_par), no traceback.
    book = _make_workbook()
    book["Général"] = [row[:2] + row[3:] for row in _GENERAL]  # no Zone column -> ValueError
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: book)
    excel = tmp_path / "model.xlsx"
    excel.write_text("stub")
    assert G.main(["--excel", str(excel), "--outdir", str(tmp_path / "out")]) == 1
    err = capsys.readouterr().err
    assert err.startswith("ERROR: ") and "declares Zone1" in err


def test_generate_fails_when_zone1_blocks_have_no_values(tmp_path, monkeypatch):
    # An unfilled template: the Zone1 blocks exist and declare their zone, but every value
    # cell is empty — the error must say so instead of blaming the 'Zone' column.
    book = _make_workbook()
    book["REEC"] = _variant_sheet("REEC_B", [("Kqp", "double", None)])
    book["REGC"] = _variant_sheet("REGC_A", [("Iqrmax", "double", None)])
    monkeypatch.setattr(G.wb, "read_workbook", lambda _path: book)
    with pytest.raises(ValueError, match=r"Zone1 control blocks \(REEC, REGC\) carry no parameter values"):
        G.generate(Path("ignored.xlsx"), tmp_path)
