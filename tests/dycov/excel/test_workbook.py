#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the shared Excel parsing engine (``dycov/excel/workbook.py``).

Workbooks are hand-built as ``{sheet -> grid}`` (grid = list of rows of str|None), the same
shape the stdlib reader returns, so no ``.xlsx`` is needed to exercise the logic."""

from __future__ import annotations

from dycov.excel import workbook as W


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


def test_placeholder_base_unit_is_not_an_annotation():
    sheet = [
        ["Interface réseau"],
        ["REGC_A"],
        ["Paramètres", "Valeurs", "Types", "Bases pour les pu"],
        ["Lvplsw", "true", "boolean", "-"],
        ["IqrMaxPu", "1.5", "double", "SnZone1"],
    ]

    variants = W.parse_variants({"REGC": sheet})

    assert [p.base_unit for p in variants["REGC_A"].parameters] == [None, "SnZone1"]


def test_variant_carries_its_sheet_and_table_label():
    variants = W.parse_variants({"REGC": _shared_types_sheet()})

    assert variants["REGC_A"].sheet == "REGC"
    assert variants["REGC_A"].table == "Interface réseau"


def _sheet_with_tables():
    """The IEC template's layout: two blocks, each with a table below its parameters, and a
    single-variant block whose table points sit in its ``Types`` column."""
    header = ["Paramètres (Dynawo)", "Valeurs", "Paramètres (Dynawo)", "Valeurs", "Types", None]
    return [
        ["Limiteur de courant", None, None, None, None, None, "Protections"],
        ["CurrentLimiter_2015", None, "CurrentLimiter_2020", None, None, None, "GridProtection"],
        header + ["Paramètres (Dynawo)", "Valeurs", "Types", "Descriptions"],
        ["IMaxPu", "1.1", "IMaxPu", "1.2", "double", None, "UOverPu", "1.35", "double", "Over"],
        [None] * 10,
        ["Tables IqMax(U)", None, None, None, None, None, "Table tDecl(U_lvrt)"],
        ["TableIqMaxUwt", None, None, None, None, None, "TabletUunderUwtfilt"],
        ["U (pu)", None, "IqMax (pu)", None, None, None, "U (pu)", None, "tDecl (s)"],
        ["U1", "0", "IqMax1", "1.0", None, None, "U1", "0.8", "tDecl1", "0.2"],
        ["U2", "0.5", "IqMax2", None, None, None, "U2", None, "tDecl2", None],
        ["U3", "/", "IqMax3", "1.2", None, None, "U3", "0.9", "tDecl3", "1.5"],
    ]


def test_a_table_gives_its_points_to_every_variant_of_its_block():
    variants = W.parse_variants({"Limiteurs": _sheet_with_tables()})

    for name in ("CurrentLimiter_2015", "CurrentLimiter_2020"):
        points = [(p.name, p.value) for p in variants[name].parameters if p.name.startswith("T")]
        assert points == [
            ("TableIqMaxUwt11", "0"),
            ("TableIqMaxUwt12", "1.0"),
            ("TableIqMaxUwt21", "0.5"),
            ("TableIqMaxUwt32", "1.2"),
        ]


def test_the_first_point_of_a_table_carries_its_title():
    variants = W.parse_variants({"Limiteurs": _sheet_with_tables()})

    points = [p for p in variants["CurrentLimiter_2015"].parameters if p.name.startswith("T")]
    assert [p.comment for p in points] == ["Tables IqMax(U)", None, None, None]
    assert {p.type for p in points} == {"double"}


def test_the_rows_of_a_table_are_not_parameters_of_their_own():
    variants = W.parse_variants({"Limiteurs": _sheet_with_tables()})

    assert [(p.name, p.value) for p in variants["GridProtection"].parameters] == [
        ("UOverPu", "1.35"),
        ("TabletUunderUwtfilt11", "0.8"),
        ("TabletUunderUwtfilt12", "0.2"),
        ("TabletUunderUwtfilt31", "0.9"),
        ("TabletUunderUwtfilt32", "1.5"),
    ]


def test_points_listed_one_per_row_are_still_parameters():
    sheet = [
        ["Protections"],
        ["GridProtection"],
        ["Paramètres (Dynawo)", "Valeurs", "Types"],
        ["UOverPu", "1.35", "double"],
        ["TabletUoverUwtfilt11", "1.1", "double"],
        ["TabletUoverUwtfilt12", "100", "double"],
    ]

    variants = W.parse_variants({"Protections": sheet})

    assert [(p.name, p.value) for p in variants["GridProtection"].parameters] == [
        ("UOverPu", "1.35"),
        ("TabletUoverUwtfilt11", "1.1"),
        ("TabletUoverUwtfilt12", "100"),
    ]
