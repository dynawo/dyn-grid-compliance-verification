#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""Reference-curve description: the ``Signaux zone 1`` / ``Signaux zone 3`` sheets.

Each sheet carries two tables and one folder cell:

* the signals table, which maps each DyCoV curve name to the column that holds it in the user's
  ``.csv`` files;
* the tests table, which names the ``.csv`` file of every test, identified by its DyCoV
  ``PCS.Benchmark.OperatingCondition``;
* the folder those ``.csv`` files live in.

Both the curve names and the test ids are read from their own columns: the tool never matches on
the sheet's descriptive text, so the wording stays free.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import workbook as wb

SHEETS = {"Zone1": "Signaux zone 1", "Zone3": "Signaux zone 3"}

_CURVE_HEADER = "nom dycov"
_COLUMN_HEADER = "variable associee"
_TEST_HEADER = "test dycov"
_FILE_HEADER = "fichier de resultats"
_FOLDER_LABEL = "dossier de resultats"


@dataclass
class Test:
    """One row of the tests table: the DyCoV test and the file holding its reference curves."""

    name: str
    curves_file: str


@dataclass
class ZoneSignals:
    """One signal sheet: the curve mapping, the tests and the folder holding the ``.csv`` files."""

    zone: str
    curves: dict = field(default_factory=dict)
    tests: list = field(default_factory=list)
    folder: str | None = None


def _norm(value) -> str:
    return wb._strip_accents(value) if isinstance(value, str) else ""


def _header_columns(grid, wanted: dict) -> tuple[int, dict] | None:
    """The first row holding every header in *wanted*, as ``(row, {key -> column})``."""
    for row_idx, row in enumerate(grid):
        found = {}
        for col, value in enumerate(row):
            text = _norm(value)
            for key, header in wanted.items():
                if header in text and key not in found:
                    found[key] = col
        if len(found) == len(wanted):
            return row_idx, found
    return None


def _labelled_value(grid, label: str) -> str | None:
    """The value that follows a label cell: to its right, or in the cell just below it."""
    marker = _norm(label)
    for row_idx, row in enumerate(grid):
        for col, value in enumerate(row):
            if marker not in _norm(value):
                continue
            right = wb._cell(grid, row_idx, col + 1)
            if right:
                return right.strip()
            below = wb._cell(grid, row_idx + 1, col)
            if below:
                return below.strip()
    return None


def _parse_curves(grid) -> dict:
    located = _header_columns(grid, {"curve": _CURVE_HEADER, "column": _COLUMN_HEADER})
    if located is None:
        raise ValueError(
            f"the signals table needs a '{_CURVE_HEADER}' column next to "
            f"'{_COLUMN_HEADER}': it is what ties each quantity to a DyCoV curve."
        )
    header_row, columns = located
    curves = {}
    for row in range(header_row + 1, len(grid)):
        name = wb._cell(grid, row, columns["curve"])
        if not name and not wb._cell(grid, row, 0):
            break  # end of the table: the rest of the sheet holds the tests
        if not name or name == wb._NOT_APPLICABLE:
            continue
        column = wb._cell(grid, row, columns["column"])
        if column and column != wb._NOT_APPLICABLE:
            curves[name.strip()] = column.strip()
    return curves


def _parse_tests(grid) -> list:
    # An untouched sheet describes no test at all, and must not stop the model inputs.
    located = _header_columns(grid, {"test": _TEST_HEADER, "file": _FILE_HEADER})
    if located is None:
        return []
    header_row, columns = located
    tests = []
    for row in range(header_row + 1, len(grid)):
        name = wb._cell(grid, row, columns["test"])
        curves_file = wb._cell(grid, row, columns["file"])
        if not name or name == wb._NOT_APPLICABLE:
            continue
        if not curves_file or curves_file == wb._NOT_APPLICABLE:
            continue
        tests.append(Test(name=name.strip(), curves_file=curves_file.strip()))
    return tests


def parse_zone_signals(workbook: dict, zone: str) -> ZoneSignals:
    """Parse one signal sheet.

    Parameters
    ----------
    workbook: dict
        The whole workbook, as ``{sheet name -> grid}``.
    zone: str
        Zone whose sheet is read, ``Zone1`` or ``Zone3``.

    Returns
    -------
    ZoneSignals
        What the sheet describes; an absent sheet describes nothing.
    """
    sheet_name = SHEETS[zone]
    if sheet_name not in workbook:
        return ZoneSignals(zone=zone)
    grid = workbook[sheet_name]
    tests = _parse_tests(grid)
    if not tests:
        return ZoneSignals(zone=zone)
    return ZoneSignals(
        zone=zone,
        curves=_parse_curves(grid),
        tests=tests,
        folder=_labelled_value(grid, _FOLDER_LABEL),
    )


def parse_signals(workbook: dict) -> dict:
    """Parse both signal sheets.

    Parameters
    ----------
    workbook: dict
        The whole workbook, as ``{sheet name -> grid}``.

    Returns
    -------
    dict
        ``{zone -> ZoneSignals}`` for both zones.
    """
    return {zone: parse_zone_signals(workbook, zone) for zone in SHEETS}
