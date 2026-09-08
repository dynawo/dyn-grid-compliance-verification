#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The synthetic workbook the Excel -> DyCoV input generator tests read.

The tool lives under ``tools/`` (outside the ``dycov`` package), so it is imported by path. The
synthetic workbook here is the smallest one ``generate`` accepts: a PV ``S+Aux+i`` plant.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "dynawo_inputs"
if str(_TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOL_DIR))

ZONE1_ROWS = {
    "SnZone1": "100", "Z_cc_TG": "0.1", "R_cc_TG / X_cc_TG": "0", "ConverterLVControl": "True",
    "r_TG": "1", "Un1": "33", "Un2": "0.7", "Pmax_injection_z1": "1", "Pmax_soutirage_z1": "0",
    "Qmax_z1": "0.4", "Qmin_z1": "-0.4", "P_share": "1", "Q_share": "1",
}
ZONE3_ROWS = {
    "SnZone3": "100", "Topologie": "S+Aux+i", "Un_PDR": "63", "Pmax_injection_PDR": "90",
    "Pmax_soutirage_PDR": "0", "Qmax_PDR": "30", "Qmin_PDR": "-30", "Z_cc_TP": "0.18",
    "R_cc_TP / X_cc_TP": "0", "N_prises": "20", "r_min": "0.9", "r_max": "1.1", "Un1": "33",
    "Sn_A": "2", "r_TA": "1", "Z_cc_TA": "0.1", "R_cc_TA / X_cc_TA": "0", "P_A": "1", "Q_A": "0.5",
    "alpha": "1.5", "beta": "2.5", "R_rc": "0.2", "X_rc": "1", "B_rc": "0", "G_rc": "0",
}

GENERAL = [
    ["Type de bloc", "Choix", "Zone", None, "Combinaison sélectionnée (clé Model Map)",
     "Zone3 lib", "Zone3 prefix", "Zone1 lib", "Zone1 prefix"],
    ["REPC", "REPC_A", "Zone3", None, "REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun"],
    ["REEC", "REEC_B", "Zone1;Zone3"], ["REGC", "REGC_A", "Zone1;Zone3"],
    ["WTGT", "Aucun", "Zone1;Zone3"], ["WTGP", "Aucun", "Zone1;Zone3"],
    ["WTGA", "Aucun", "Zone1;Zone3"], ["WTGQ", "Aucun", "Zone1;Zone3"],
]
MODEL_MAP = [
    ["Key", "Zone3_lib", "Zone3_prefix", "Zone1_lib", "Zone1_prefix"],
    ["REGC_A|REEC_B|Aucun|Aucun|Aucun|Aucun", "PhotovoltaicsWeccCurrentSource", "photovoltaics_",
     "PhotovoltaicsWeccCurrentSourceNoPlantControl", "photovoltaics_"],
]


def variant_sheet(variant_name: str, params: list) -> list:
    """A control-param sheet: the variant name sits on the row above the 'Parameter' header."""
    grid = [[variant_name], ["Parameter", "Type", "Value"]]
    grid += [[name, typ, val] for name, typ, val in params]
    return grid


def make_workbook() -> dict:
    """The synthetic workbook ``generate`` reads, as ``{sheet -> grid}``."""
    zone1_grid = [["intro"], ["Paramètres", "Descriptions", "Valeurs", "Unités", "Commentaires"]]
    zone1_grid += [[k, "d", v, "u", "c"] for k, v in ZONE1_ROWS.items()]
    zone3_grid = [["defs"],
                  ["Catégorie", "Paramètres", "Descriptions", "Valeurs", "Unités", "Cmt"]]
    zone3_grid += [["cat", k, "d", v, "u", "c"] for k, v in ZONE3_ROWS.items()]
    return {
        "Général": GENERAL,
        "Model Map": MODEL_MAP,
        "Zone1a": zone1_grid,
        "Zone3": zone3_grid,
        "REPC": variant_sheet("REPC_A", [("FreqFlag", "boolean", "true")]),
        "REEC": variant_sheet("REEC_B", [("Kqp", "double", "1.0"), ("QFlag", "boolean", "true")]),
        "REGC": variant_sheet("REGC_A", [("Iqrmax", "double", "20")]),
    }


def workbook_with(zone1_overrides: dict) -> dict:
    """The synthetic workbook with some ``Zone1a`` values replaced."""
    book = make_workbook()
    book["Zone1a"] = [
        [row[0], "d", zone1_overrides[row[0]], "u", "c"] if row[0] in zone1_overrides else row
        for row in book["Zone1a"]
    ]
    return book
