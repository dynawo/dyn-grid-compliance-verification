#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""What the workbooks offer the user to fill in: a True/False list on every boolean parameter,
and the rows of the active and reactive power at node 1 in the signals of zone 1."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from dycov.excel import signals
from dycov.excel import workbook as W

ROOT = Path(__file__).resolve().parents[3]
TEMPLATES = sorted((ROOT / "workbooks").glob("Producer_*.xlsx"))
EXAMPLES = sorted((ROOT / "examples").glob("**/Excel/Producer.xlsx"))
MODEL_EXAMPLES = sorted((ROOT / "examples" / "Model").glob("**/Excel/Producer.xlsx"))
_MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _letters(col: int) -> str:
    letters = ""
    col += 1
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _boolean_cells(book: dict) -> dict:
    """``{sheet -> {cell}}`` of the value cells of the boolean parameters of the control sheets."""
    found = {}
    for sheet, grid in book.items():
        header = W._find_header_row(grid)
        if header is None or W._strip_accents(sheet).startswith(W._CONFIG_SHEET):
            continue
        labels = W._find_table_labels(grid, header - 2)
        for param_col in W._find_column_groups(grid, header):
            columns = W._group_columns(grid, header, param_col, labels)
            for row in range(header + 1, len(grid)) if columns else ():
                name = W._cell(grid, row, columns.param)
                kind = W._cell(grid, row, columns.type)
                if name and kind and name != W._NOT_APPLICABLE and W._map_type(kind) == "BOOL":
                    found.setdefault(sheet, set()).add(f"{_letters(columns.value)}{row + 1}")
    return found


def _cells_of(sqref: str) -> set:
    cells = set()
    for ref in sqref.split():
        first, _, last = ref.partition(":")
        last = last or first
        (c0, r0), (c1, r1) = (re.match(r"([A-Z]+)(\d+)", r).groups() for r in (first, last))
        for col in range(W._col_letters_to_index(c0), W._col_letters_to_index(c1) + 1):
            cells |= {f"{_letters(col)}{row}" for row in range(int(r0), int(r1) + 1)}
    return cells


def _true_false_lists(path: Path) -> dict:
    """``{sheet -> {cell}}`` the True/False lists of the workbook cover."""
    covered = {}
    with zipfile.ZipFile(path) as archive:
        for sheet, target in W._read_sheet_index(archive):
            root = ET.fromstring(archive.read(target))
            for validation in root.iter(f"{_MAIN}dataValidation"):
                formula = validation.findtext(f"{_MAIN}formula1") or ""
                if validation.get("type") == "list" and formula == '"True,False"':
                    covered.setdefault(sheet, set()).update(_cells_of(validation.get("sqref")))
    return covered


@pytest.mark.parametrize("path", TEMPLATES + EXAMPLES, ids=lambda p: str(p.relative_to(ROOT)))
def test_every_boolean_parameter_offers_true_or_false(path):
    booleans = _boolean_cells(W.read_workbook(path))
    covered = _true_false_lists(path)

    assert booleans
    assert {sheet: cells - covered.get(sheet, set()) for sheet, cells in booleans.items()} == {
        sheet: set() for sheet in booleans
    }


@pytest.mark.parametrize("path", MODEL_EXAMPLES, ids=lambda p: str(p.relative_to(ROOT)))
def test_the_signals_of_zone_1_describe_the_powers_at_node_1(path):
    zone1 = signals.parse_zone_signals(W.read_workbook(path), "Zone1", "Unit")

    assert zone1.curves["InternalNode1_BUS_ActivePower"] == "InternalNode1_BUS_ActivePower"
    assert zone1.curves["InternalNode1_BUS_ReactivePower"] == "InternalNode1_BUS_ReactivePower"
