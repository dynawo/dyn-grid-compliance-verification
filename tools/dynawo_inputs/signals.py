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

* the signals table, whose rows are the quantities to provide, with the column that holds each
  one in the user's ``.csv`` files;
* the tests table, whose rows are the DTR cases to run, with the ``.csv`` file of each one;
* the folder those ``.csv`` files live in.

What every row *means* to DyCoV — the curve name, and the operating condition a case runs as —
comes from ``excel_names.ini``, so the sheets keep carrying only what the user fills in.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import excel_names as names
import workbook as wb


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


def _header_columns(grid, wanted: dict) -> tuple[int, dict] | None:
    """The first row holding every header in *wanted*, as ``(row, {key -> column})``."""
    for row_idx, row in enumerate(grid):
        found = {}
        for col, value in enumerate(row):
            text = names.normalize(value)
            for key, header in wanted.items():
                if header in text and key not in found:
                    found[key] = col
        if len(found) == len(wanted):
            return row_idx, found
    return None


def _column_of(grid, header: str) -> int | None:
    """The column of the cell holding *header*, wherever it sits in the sheet."""
    for row in grid:
        for col, value in enumerate(row):
            if header in names.normalize(value):
                return col
    return None


def _labelled_value(grid, label: str) -> str | None:
    """The value that follows a label cell: to its right, or in the cell just below it."""
    for row_idx, row in enumerate(grid):
        for col, value in enumerate(row):
            if label not in names.normalize(value):
                continue
            right = wb._cell(grid, row_idx, col + 1)
            if right:
                return right.strip()
            below = wb._cell(grid, row_idx + 1, col)
            if below:
                return below.strip()
    return None


def _parse_curves(grid, zone: str, generator_id: str) -> dict:
    known = names.curves(zone, generator_id)
    located = _header_columns(
        grid, {"label": names.anchor("signal_label"), "column": names.anchor("signal_column")}
    )
    if located is None:
        return {}
    header_row, columns = located
    mapped = {}
    for row in range(header_row + 1, len(grid)):
        label = wb._cell(grid, row, columns["label"])
        if not label:
            break  # end of the table: the rest of the sheet holds the tests
        curve = known.get(names.normalize(label))
        column = wb._cell(grid, row, columns["column"])
        if curve and column and column != names.marker("not_applicable"):
            mapped[curve] = column.strip()
    return mapped


def _test_key(case: str, seen: dict) -> tuple[str, str]:
    """The two keys a case row may be defined by: its own name, and its name plus its position."""
    ordinal = seen[case] = seen.get(case, 0) + 1
    return f"{case}/{ordinal}", case


def _suffixed(name: str, curves_file: str, suffix: str) -> Test:
    if not suffix:
        return Test(name=name, curves_file=curves_file)
    stem, dot, extension = curves_file.rpartition(".")
    suffixed_file = f"{stem}{suffix}{dot}{extension}" if dot else f"{curves_file}{suffix}"
    return Test(name=name + suffix, curves_file=suffixed_file)


def _parse_tests(grid, zone: str, suffixes: tuple = ("",)) -> list:
    known = names.tests(zone)
    case_column = None
    for key in ("test_case", "test_fiche"):
        case_column = _column_of(grid, names.anchor(key))
        if case_column is not None:
            break
    file_column = _column_of(grid, names.anchor("test_file"))
    if case_column is None or file_column is None:
        return []

    tests, seen = [], {}
    for row in range(len(grid)):
        case = wb._cell(grid, row, case_column)
        curves_file = wb._cell(grid, row, file_column)
        if not case:
            continue
        with_ordinal, plain = _test_key(names.normalize(case), seen)
        name = known.get(with_ordinal, known.get(plain))
        if not name or not curves_file or curves_file == names.marker("not_applicable"):
            continue
        tests += [_suffixed(name, curves_file.strip(), suffix) for suffix in suffixes]
    return tests


def parse_zone_signals(
    workbook: dict, zone: str, generator_id: str, storage: bool = False
) -> ZoneSignals:
    """Parse one signal sheet.

    Parameters
    ----------
    workbook: dict
        The whole workbook, as ``{sheet name -> grid}``.
    zone: str
        Zone whose sheet is read, ``Zone1`` or ``Zone3``.
    generator_id: str
        Id of the generator block, which names its own curves.
    storage: bool
        Whether the plant is a storage one, whose every case runs twice (injecting and consuming),
        so one row of the tests table describes two tests and two ``.csv`` files.

    Returns
    -------
    ZoneSignals
        What the sheet describes; an absent or unfilled sheet describes nothing.
    """
    sheet_name = names.sheet(f"signals_{zone.lower()}")
    if sheet_name not in workbook:
        return ZoneSignals(zone=zone)
    grid = workbook[sheet_name]
    tests = _parse_tests(grid, zone, names.test_suffixes() if storage else ("",))
    if not tests:
        return ZoneSignals(zone=zone)
    return ZoneSignals(
        zone=zone,
        curves=_parse_curves(grid, zone, generator_id),
        tests=tests,
        folder=_labelled_value(grid, names.anchor("curves_folder")),
    )


def parse_signals(workbook: dict, generator_id: str, storage: bool = False) -> dict:
    """Parse both signal sheets.

    Parameters
    ----------
    workbook: dict
        The whole workbook, as ``{sheet name -> grid}``.
    generator_id: str
        Id of the generator block, which names its own curves.
    storage: bool
        Whether the plant is a storage one (see ``parse_zone_signals``).

    Returns
    -------
    dict
        ``{zone -> ZoneSignals}`` for both zones.
    """
    return {
        zone: parse_zone_signals(workbook, zone, generator_id, storage)
        for zone in ("Zone1", "Zone3")
    }
