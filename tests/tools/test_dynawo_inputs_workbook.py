# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Tests for the shared Excel parsing engine (``tools/dynawo_inputs/workbook.py``).

Workbooks are hand-built as ``{sheet -> grid}`` (grid = list of rows of str|None), the same
shape the stdlib reader returns, so no ``.xlsx`` is needed to exercise the logic."""

from __future__ import annotations

import sys
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parents[2] / "tools" / "dynawo_inputs"
sys.path.insert(0, str(_TOOL_DIR))

import workbook as W  # noqa: E402


def _shared_types_sheet():
    """The template's layout: ``Paramètres | Valeurs`` per variant, one shared ``Types``."""
    return [
        ["Interface réseau"],
        ["REGC_A", None, "REGC_B", None],
        [
            "Paramètres (Dynawo)",
            "Valeurs",
            "Paramètres\n(Dynawo)",
            "Valeurs",
            "Types",
            "Unités",
            "Bases pour les pu",
        ],
        ["IqrMaxPu", "1.5", "IqrMaxPu", "2.5", "double", "pu", "SnZone1"],
        ["Lvplsw", "true", None, None, "boolean", "-", "-"],
    ]


def test_shared_types_column_is_used_by_every_variant_of_the_block():
    variants = W.parse_variants({"REGC": _shared_types_sheet()})

    assert set(variants) == {"REGC_A", "REGC_B"}
    first = variants["REGC_A"].parameters[0]
    second = variants["REGC_B"].parameters[0]
    assert (first.name, first.type, first.value) == ("IqrMaxPu", "double", "1.5")
    assert (second.name, second.type, second.value) == ("IqrMaxPu", "double", "2.5")


def test_shared_types_layout_keeps_base_unit_and_sparse_rows():
    variants = W.parse_variants({"REGC": _shared_types_sheet()})

    assert variants["REGC_A"].parameters[0].base_unit == "SnZone1"
    assert [p.name for p in variants["REGC_A"].parameters] == ["IqrMaxPu", "Lvplsw"]
    assert [p.name for p in variants["REGC_B"].parameters] == ["IqrMaxPu"]


def test_per_variant_type_column_still_parses():
    sheet = [
        ["Drive-Train"],
        ["WTGT_A", None, None, "WTGT_B"],
        ["Paramètres", "Types", "Valeurs", "Paramètres", "Types", "Valeurs"],
        ["Ht", "double", "4", "Ht", "double", "5"],
    ]

    variants = W.parse_variants({"Mechanical Part": sheet})

    assert [(p.type, p.value) for p in variants["WTGT_A"].parameters] == [("double", "4")]
    assert [(p.type, p.value) for p in variants["WTGT_B"].parameters] == [("double", "5")]


def test_types_column_is_not_borrowed_from_the_next_table_block():
    sheet = [
        ["Aerodynamic", None, "Torque Control"],
        ["WTGA_A", None, "WTGQ_A", None, None],
        ["Paramètres", "Valeurs", "Paramètres", "Valeurs", "Types"],
        ["Ka", "0.007", "TFlag", "true", "boolean"],
    ]

    variants = W.parse_variants({"Mechanical Part": sheet})

    assert set(variants) == {"WTGQ_A"}


def test_electrical_table_of_a_zone_sheet_is_not_a_variant_table():
    zone1a = [
        ["Le schéma de base pour la zone 1 est le suivant :"],
        ["Paramètres", "Descriptions", "Valeurs", "Unités"],
        ["SnZone1", "puissance", "90", "MVA"],
    ]

    assert W.parse_variants({"Zone1a": zone1a}) == {}


def test_not_applicable_name_drops_the_row_for_that_variant_only():
    sheet = [
        ["Contrôle convertisseur"],
        ["REEC_A", None, "REEC_B", None],
        ["Paramètres", "Valeurs", "Paramètres", "Valeurs", "Types"],
        ["PFlag", "true", "/", "/", "boolean"],
        ["VFlag", "false", "VFlag", "false", "boolean"],
    ]

    variants = W.parse_variants({"REEC": sheet})

    assert [p.name for p in variants["REEC_A"].parameters] == ["PFlag", "VFlag"]
    assert [p.name for p in variants["REEC_B"].parameters] == ["VFlag"]


def test_not_applicable_value_leaves_the_parameter_unfilled():
    sheet = [
        ["Interface réseau"],
        ["REGC_A"],
        ["Paramètres", "Valeurs", "Types"],
        ["KpPLL", "/", "double"],
    ]

    variants = W.parse_variants({"REGC": sheet})

    assert [(p.name, p.value) for p in variants["REGC_A"].parameters] == [("KpPLL", None)]


def test_variant_carries_its_sheet_and_table_label():
    variants = W.parse_variants({"REGC": _shared_types_sheet()})

    assert variants["REGC_A"].sheet == "REGC"
    assert variants["REGC_A"].table == "Interface réseau"
