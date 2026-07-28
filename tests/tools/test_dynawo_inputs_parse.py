# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Tests for the WECC front-end parsing/resolution (``tools/dynawo_inputs/parse.py``).

Workbooks are hand-built as ``{sheet -> grid}`` (grid = list of rows of str|None), the same
shape the stdlib reader returns, so no ``.xlsx`` is needed to exercise the logic."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "dynawo_inputs"
sys.path.insert(0, str(_TOOL_DIR))

import parse as P  # noqa: E402


def _general(*choices):
    rows = [["Type de bloc", "Choix"]]
    rows += [[block, choice] for block, choice in choices]
    return rows


_MODEL_MAP = [
    [None, None, None],  # title area above the table
    ["Key", "Zone3_lib", "Zone3_prefix", "Zone1_lib", "Zone1_prefix"],
    [
        "REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun",
        "PhotovoltaicsWeccCurrentSource",
        "photovoltaics_",
        "PhotovoltaicsWeccCurrentSourceNoPlantControl",
        "photovoltaics_",
    ],
    [
        "REGC_A|REEC_A|Aucun|Aucun|Aucun|Aucun",
        "WTG4BWeccCurrentSource",
        "WTG4B_",
        "WT4BWeccCurrentSource",
        "WT4B_",
    ],
    ["REGC_A|REEC_C|Aucun|Aucun|Aucun|Aucun", "BESSWeccCurrentSource", "BESS_",
     "BESSWeccCurrentSourceNoPlantControl", "BESS_"],
]


def _workbook(general):
    return {"Général": general, "Model Map": _MODEL_MAP}


def test_build_key_orders_blocks():
    config_wb = _workbook(
        _general(
            ("REPC", "REPC_A"), ("REEC", "REEC_B"), ("REGC", "REGC_A"),
            ("WTGT", "Aucun"), ("WTGP", "Aucun"), ("WTGA", "Aucun"), ("WTGQ", "Aucun"),
        )
    )
    import generate_par as dp

    assert P.build_key(dp.parse_config(config_wb)) == "REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun"


def test_resolve_models_pv():
    wb = _workbook(
        _general(
            ("REPC", "REPC_A"), ("REEC", "REEC_B"), ("REGC", "REGC_A"),
            ("WTGT", "Aucun"), ("WTGP", "Aucun"), ("WTGA", "Aucun"), ("WTGQ", "Aucun"),
        )
    )
    resolved = P.resolve_models(wb)
    assert resolved["zone3_lib"] == "PhotovoltaicsWeccCurrentSource"
    assert resolved["zone3_prefix"] == "photovoltaics_"
    assert resolved["zone1_lib"] == "PhotovoltaicsWeccCurrentSourceNoPlantControl"
    assert resolved["zone1_prefix"] == "photovoltaics_"


def test_resolve_models_unknown_combination_raises():
    wb = _workbook(
        _general(
            ("REPC", "REPC_A"), ("REEC", "REEC_A"), ("REGC", "REGC_A"),
            ("WTGT", "Aucun"), ("WTGP", "WTGP_B"), ("WTGA", "Aucun"), ("WTGQ", "Aucun"),
        )
    )
    with pytest.raises(ValueError, match="not found in 'Model Map'"):
        P.resolve_models(wb)


def test_technology_and_template():
    assert P.technology("PhotovoltaicsWeccCurrentSource") == "PV"
    assert P.technology("WTG4BWeccCurrentSource") == "Wind"
    assert P.technology("WeccWT3CurrentSource2") == "Wind"
    assert P.technology("BESSWeccCurrentSource") == "BESS"
    assert P.template_for("PhotovoltaicsWeccCurrentSource") == "model_PPM"
    assert P.template_for("WTG4BWeccCurrentSource") == "model_PPM"
    assert P.template_for("BESSWeccCurrentSource") == "model_BESS"


def test_parse_zone_zone1_layout_name_A_value_C():
    grid = [
        ["Le schéma de base ..."],
        ["Paramètres", "Descriptions", "Valeurs", "Unités", "Commentaires"],
        ["SnZone1", "apparent power", "1.1", "MVA", "note"],
        ["ConverterLVControl", "control point", "True", "-", "note"],
        ["Un1", "HV nominal", "33", "kV", "note"],
        [None, None, None, None, None],
        ["Si le parc contient ...", None, None, None, None],  # trailing note, must be ignored
    ]
    out = P.parse_zone({"Zone1a": grid}, "Zone1a")
    assert out == {"SnZone1": "1.1", "ConverterLVControl": "True", "Un1": "33"}


def test_parse_zone_zone3_layout_name_B_value_D():
    grid = [
        ["S", "Zone 1 + Transformateur principal"],  # topology defs above the table
        ["Catégorie", "Paramètres", "Descriptions", "Valeurs", "Unités", "Commentaires"],
        ["Paramètres généraux", "SnZone3", "total power", "55", "MVA", "note"],
        [None, "Topologie", None, "S", "-", None],
        [None, "Un_PDR", "PDR nominal", "63", "kV", "note"],
        ["Transformateur principal", "Z_cc_TP", "sc impedance", "0.18", "pu", "note"],
    ]
    out = P.parse_zone({"Zone3": grid}, "Zone3")
    assert out == {"SnZone3": "55", "Topologie": "S", "Un_PDR": "63", "Z_cc_TP": "0.18"}


def test_zone1_sheets_lists_in_order():
    wb = {"Général": [], "Zone1a": [], "Zone1b": [], "Zone3": []}
    assert P.zone1_sheets(wb) == ["Zone1a", "Zone1b"]


def test_parse_control_params_maps_type_and_carries_comments():
    wb = {
        "Général": _general(("REEC", "REEC_B")),
        "REEC": [
            ["Electrical Control"],  # table-name row (N-2)
            ["REEC_B"],  # variant row (N-1)
            ["Parameter", "Type", "Value", "Base unit", "Comment"],
            ["Kqp", "double", "1.0", "", ""],
            ["QFlag", "boolean", "true", "", "reactive flag"],
            ["tIq", "double", "0.02", "s", ""],
        ],
    }
    [(block, variant, params)] = P.parse_control_params(wb)
    assert (block, variant) == ("REEC", "REEC_B")
    # first valued parameter heads the section (design 8.3: sheet + table | variant)
    assert params[0]["comments"][:2] == ["REEC", "Electrical Control | REEC_B"]
    # Excel type mapped to the Dynawo convention; per-param comment / base unit merged
    assert params[0]["type"] == "DOUBLE"
    assert {p["name"]: p["type"] for p in params}["QFlag"] == "BOOL"
    assert params[1]["comments"][-1] == "reactive flag"
    assert params[2]["comments"][-1] == "Base unit: s"
