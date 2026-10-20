#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Tests for the generating units (``dycov/excel/units.py``): one per ``Zone1<x>`` sheet."""

from __future__ import annotations

import copy

import pytest
from workbooks import make_workbook

from dycov.excel import parse as P
from dycov.excel import units as U


def _with_units(count: int) -> dict:
    """The synthetic workbook with its ``Zone1a`` duplicated into *count* sheets."""
    book = make_workbook()
    for letter in "bcd"[: count - 1]:
        book[f"Zone1{letter}"] = copy.deepcopy(book["Zone1a"])
    return book


def _one_model_per_sheet(monkeypatch):
    """Stand in for the workbook saying which model each unit is, which it cannot do yet."""
    monkeypatch.setattr(
        P,
        "resolve_unit_models",
        lambda workbook, sheets: [P.resolve_models(workbook) for _sheet in sheets],
    )


def test_a_single_unit_takes_the_producer_name_and_its_technology_id():
    (unit,) = U.generating_units(make_workbook(), "S+Aux", "Producer")

    assert (unit.zone1_file, unit.gen_id, unit.plant_id) == ("Producer", "PV_Array", "PV_Array")
    assert unit.model["zone3_lib"] == "PhotovoltaicsWeccCurrentSource"
    assert P.sheet_of(unit.zone1) == "Zone1a"
    assert unit.lv_control


def test_a_multiple_plant_is_refused_until_the_workbook_says_each_unit_s_model():
    with pytest.raises(ValueError, match="no sheet says which model each unit is"):
        U.generating_units(_with_units(2), "M+Aux", "Producer")


def test_the_units_of_a_multiple_plant_are_numbered_in_workbook_order(monkeypatch):
    _one_model_per_sheet(monkeypatch)

    units = U.generating_units(_with_units(3), "M", "Producer")

    assert [P.sheet_of(u.zone1) for u in units] == ["Zone1a", "Zone1b", "Zone1c"]
    assert [u.zone1_file for u in units] == ["Producer_G1", "Producer_G2", "Producer_G3"]
    assert [u.plant_id for u in units] == ["PV_Array1", "PV_Array2", "PV_Array3"]
    assert {u.gen_id for u in units} == {"PV_Array"}


def test_a_single_unit_topology_refuses_several_zone1_sheets():
    with pytest.raises(ValueError, match="single generating unit, and the workbook has 2"):
        U.generating_units(_with_units(2), "S", "Producer")


def test_a_multiple_topology_refuses_a_single_zone1_sheet():
    with pytest.raises(ValueError, match="duplicate it once per unit"):
        U.generating_units(make_workbook(), "M+i", "Producer")


def test_a_workbook_without_zone1_sheet_is_refused():
    book = make_workbook()
    del book["Zone1a"]

    with pytest.raises(ValueError, match="no Zone1 sheet"):
        U.generating_units(book, "S", "Producer")


def test_the_units_of_a_plant_share_the_voltage_of_its_internal_node(monkeypatch):
    _one_model_per_sheet(monkeypatch)
    book = _with_units(2)
    book["Zone1b"] = [
        [row[0], "d", "20", "u", "c"] if row[0] == "Un1" else row for row in book["Zone1b"]
    ]

    with pytest.raises(ValueError, match=r"different nominal voltages .*Zone1a: 33, Zone1b: 20"):
        U.generating_units(book, "M", "Producer")
