#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the WECC front-end parsing/resolution (``tools/dynawo_inputs/parse.py``).

Workbooks are hand-built as ``{sheet -> grid}`` (grid = list of rows of str|None), the same
shape the stdlib reader returns, so no ``.xlsx`` is needed to exercise the logic."""

from __future__ import annotations

import parse as P
import pytest


def _general(*choices, key=None):
    """A ``Général`` grid: block table (with its ``Zone`` column) plus the horizontal derived
    table, whose first column holds the Excel-cached Model-Map key. The key header is
    deliberately not named ``Key`` — the parser anchors on ``Zone3 lib`` and never reads it."""
    rows = [
        [
            "Type de bloc",
            "Choix",
            "Zone",
            None,
            "Combinaison sélectionnée (clé Model Map)",
            "Zone3 lib",
            "Zone3 prefix",
            "Zone1 lib",
            "Zone1 prefix",
        ]
    ]
    for i, (block, choice) in enumerate(choices):
        row = [block, choice, "Zone3" if block == "REPC" else "Zone1;Zone3"]
        if i == 0:
            row += [None, key]
        rows.append(row)
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
    [
        "REGC_A|REEC_C|Aucun|Aucun|Aucun|Aucun",
        "BESSWeccCurrentSource",
        "BESS_",
        "BESSWeccCurrentSourceNoPlantControl",
        "BESS_",
    ],
]


def _workbook(general):
    return {"Général": general, "Model Map": _MODEL_MAP}


def test_read_selected_key_is_read_not_rebuilt():
    # The key is the Excel-cached cell under the derived-table header, read verbatim: the tool
    # knows nothing of the blocks that form it (here it even disagrees with the selection).
    wb = _workbook(_general(("REPC", "REPC_A"), key="Whatever|Excel|Computed"))
    assert P.read_selected_key(wb) == "Whatever|Excel|Computed"


def test_read_selected_key_empty_cell_asks_for_excel_save():
    # A workbook saved without cached formula values (non-Excel writer) must fail clearly.
    wb = _workbook(_general(("REPC", "REPC_A"), key=None))
    with pytest.raises(ValueError, match="Excel and save"):
        P.read_selected_key(wb)


def test_read_selected_key_without_derived_table_raises():
    wb = _workbook([["Type de bloc", "Choix"], ["REPC", "REPC_A"]])
    with pytest.raises(ValueError, match="derived-model table"):
        P.read_selected_key(wb)


def test_resolve_models_pv():
    wb = _workbook(
        _general(
            ("REPC", "REPC_A"),
            ("REEC", "REEC_B"),
            ("REGC", "REGC_A"),
            ("WTGT", "Aucun"),
            ("WTGP", "Aucun"),
            ("WTGA", "Aucun"),
            ("WTGQ", "Aucun"),
            key="REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun",
        )
    )
    resolved = P.resolve_models(wb)
    assert resolved["zone3_lib"] == "PhotovoltaicsWeccCurrentSource"
    assert resolved["zone3_prefix"] == "photovoltaics_"
    assert resolved["zone1_lib"] == "PhotovoltaicsWeccCurrentSourceNoPlantControl"
    assert resolved["zone1_prefix"] == "photovoltaics_"


def test_resolve_models_unknown_combination_raises():
    wb = _workbook(_general(("REPC", "REPC_A"), key="REGC_A|REEC_A|Aucun|WTGP_B|Aucun|Aucun"))
    with pytest.raises(ValueError) as error:
        P.resolve_models(wb)

    message = str(error.value)
    assert "not found in 'Model Map'" in message
    # The user's own combination, where to change it, and the ones to choose from.
    assert "REGC_A|REEC_A|Aucun|WTGP_B|Aucun|Aucun" in message
    assert "'Choix' column of 'Général'" in message
    assert "REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun" in message


def test_model_map_key_header_name_is_free():
    # The map key column is located as the column left of 'Zone3_lib', whatever its header says.
    renamed = [list(row) for row in _MODEL_MAP]
    renamed[1] = ["Combinaison"] + renamed[1][1:]
    wb = {
        "Général": _general(("REPC", "REPC_A"), key="REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun"),
        "Model Map": renamed,
    }
    assert P.resolve_models(wb)["zone3_lib"] == "PhotovoltaicsWeccCurrentSource"


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
            ["QFlag", "boolean", "true", "-", "reactive flag"],
            ["tIq", "double", "0.02", "s", ""],
        ],
    }
    params = P.parse_control_params(wb)
    assert [p["block"] for p in params] == ["REEC", "REEC", "REEC"]
    # the first valued parameter opens the section, named after the variant
    assert params[0]["comments"][:1] == ["REEC_B"]
    # Excel type mapped to the Dynawo convention; per-param comment / base unit merged
    assert params[0]["type"] == "DOUBLE"
    assert {p["name"]: p["type"] for p in params}["QFlag"] == "BOOL"
    assert params[1]["comments"][-1] == "reactive flag"
    assert params[2]["comments"][-1] == "Base unit: s"


def test_parse_control_params_resolves_the_converter_voltage_base():
    wb = {
        "Général": _general(("REGC", "REGC_A")),
        "REGC": [
            ["Generator Converter"],
            ["REGC_A"],
            ["Parameter", "Type", "Value", "Base unit"],
            ["IqrMaxPu", "double", "20", "Un1 ou Un2, SnZone1"],
        ],
    }

    resolved = P.parse_control_params(wb, "Un2")
    unresolved = P.parse_control_params(wb)

    assert resolved[0]["comments"][-1] == "Base unit: Un2, SnZone1"
    assert unresolved[0]["comments"][-1] == "Base unit: Un1 ou Un2, SnZone1"


def test_parse_control_params_shortens_doubles_only():
    wb = {
        "Général": _general(("REPC", "REPC_A")),
        "REPC": [
            ["Plant Control"],
            ["REPC_A"],
            ["Parameter", "Type", "Value"],
            # Excel stores 1e-5 and 3.333 with the full 17 digits of the nearest double.
            ["tFt", "double", "1.0000000000000001E-5"],
            ["Kp", "double", "3.3330000000000002"],
            ["PMaxREPCPu", "double", "1"],
            ["FreqFlag", "boolean", "true"],
        ],
    }

    values = {p["name"]: p["value"] for p in P.parse_control_params(wb)}

    assert values == {"tFt": "1e-05", "Kp": "3.333", "PMaxREPCPu": "1", "FreqFlag": "true"}


def test_parse_control_params_flat_list_preserves_workbook_order():
    # Two selected blocks: the flat list follows the sheet order (REEC before REGC here) with
    # the block only as a provenance label — 'Général' listing REGC first must not reorder it.
    def _sheet(table, variant, rows):
        return [[table], [variant], ["Parameter", "Type", "Value"]] + rows

    wb = {
        "Général": _general(("REGC", "REGC_A"), ("REEC", "REEC_B")),
        "REEC": _sheet(
            "Electrical Control",
            "REEC_B",
            [["Kqp", "double", "1.0"], ["QFlag", "boolean", "true"]],
        ),
        "REGC": _sheet("Generator Converter", "REGC_A", [["tG", "double", "0.02"]]),
    }
    params = P.parse_control_params(wb)
    assert [(p["block"], p["name"]) for p in params] == [
        ("REEC", "Kqp"),
        ("REEC", "QFlag"),
        ("REGC", "tG"),
    ]
    # each variant's first param carries its section header, the following ones do not
    assert params[0]["comments"] == ["REEC_B"]
    assert params[1]["comments"] == []
    assert params[2]["comments"] == ["REGC_A"]


def _zone3(**rows):
    grid = [
        ["Catégorie", "Paramètres", "Descriptions", "Valeurs", "Unités", "Commentaires"],
        *([None, name, None, value, None, None] for name, value in rows.items()),
    ]
    return P.parse_zone({"Zone3": grid}, "Zone3")


def test_zone_text_names_the_sheet_of_an_absent_row():
    zone = _zone3(Un_PDR="225")

    with pytest.raises(ValueError, match="row 'Z_cc_TP' not found in sheet 'Zone3'"):
        P.zone_text(zone, "Z_cc_TP")


def test_zone_text_reports_an_empty_cell_and_offers_the_sentinel():
    zone = _zone3(Z_cc_TP=None)

    with pytest.raises(ValueError, match="row 'Z_cc_TP' in sheet 'Zone3' has no value"):
        P.zone_text(zone, "Z_cc_TP")


def test_zone_text_rejects_a_row_the_model_needs_but_the_sheet_marks_not_applicable():
    zone = _zone3(Z_cc_TA="/")

    with pytest.raises(ValueError, match="marked '/' .not applicable."):
        P.zone_text(zone, "Z_cc_TA")


def test_zone_number_quotes_the_offending_cell():
    zone = _zone3(SnZone3="55 MVA")

    with pytest.raises(ValueError, match="expects a number and holds '55 MVA'"):
        P.zone_number(zone, "SnZone3")


def test_zone_number_reads_a_plain_decimal():
    zone = _zone3(SnZone3="55.5")

    assert P.zone_number(zone, "SnZone3") == 55.5


def test_zone_value_validates_the_number_but_keeps_the_written_form():
    zone = _zone3(Un_PDR="225.0")

    assert P.zone_value(zone, "Un_PDR") == "225.0"


def test_zone_accessors_work_on_a_plain_dict_without_provenance():
    with pytest.raises(ValueError, match="not found in sheet 'the zone sheet'"):
        P.zone_text({"Un_PDR": "225"}, "Z_cc_TP")


def test_zone_optional_number_reads_a_filled_row():
    zone = _zone3(Tap_0="15")

    assert P.zone_optional_number(zone, "Tap_0") == 15.0


def test_zone_optional_number_is_none_for_an_empty_or_absent_or_not_applicable_row():
    zone = _zone3(Tap_0=None, r_0="/")

    assert P.zone_optional_number(zone, "Tap_0") is None
    assert P.zone_optional_number(zone, "r_0") is None
    assert P.zone_optional_number(zone, "Un_PDR") is None
