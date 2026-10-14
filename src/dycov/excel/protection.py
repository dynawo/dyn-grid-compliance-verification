#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) 2026 RTE
# Developed by Grupo AIA
#     marinjl@aia.es
#     omsg@aia.es
#     demiguelm@aia.es
#
"""The ride-through capability curves of the unit, as the table file its protection reads."""

from __future__ import annotations

from pathlib import Path

from dycov.excel import names
from dycov.excel import workbook as wb

# Each curve of the protection sheet, and the parameter that names the table holding it.
CURVES = (
    ("undervoltage_curve", "TabletUunderUfilt"),
    ("overvoltage_curve", "TabletUoverUfilt"),
)


def write_table_file(workbook: dict, params: list, target: Path) -> str | None:
    """Write the protection's table file next to the PAR that names it.

    The protection reads its curves from a file, so that file is part of the model the producer
    delivers. The name it takes and the name of each table in it are the parameters the workbook
    declares, which is what keeps the file and the PAR consistent. A workbook that describes no
    curve writes no file.

    Parameters
    ----------
    workbook: dict
        The whole workbook, as ``{sheet name -> grid}``.
    params: list
        Parameters of the generating unit, as the PAR carries them: the ones naming the file and
        its tables are read from here.
    target: Path
        Directory of the PAR, where the file is written.

    Returns
    -------
    str or None
        Name of the file written, or None when the workbook describes no curve.
    """
    curves = read_curves(workbook)
    if not any(curves.values()):
        return None

    filename = _parameter(params, "TablesFile")
    if not filename:
        raise ValueError(
            "the protection sheet describes the ride-through curves, but no 'TablesFile' "
            "parameter says which file holds them."
        )

    blocks = []
    for key, table_parameter in CURVES:
        points = curves[key]
        if not points:
            continue
        table = _parameter(params, table_parameter)
        if not table:
            raise ValueError(
                f"the protection sheet describes the '{key}' curve, but no "
                f"'{table_parameter}' parameter names its table."
            )
        rows = "\n".join(f"  {voltage:<8g} {time:g}" for voltage, time in points)
        blocks.append(f"double {table}({len(points)},2)\n{rows}\n")

    (Path(target) / filename).write_text("#1\n" + "\n".join(blocks), encoding="utf-8")
    return filename


def read_curves(workbook: dict) -> dict:
    """``{curve -> [(voltage, time)]}`` as the protection sheet describes them, in its order."""
    grid = _protection_sheet(workbook)
    if grid is None:
        return {key: [] for key, _ in CURVES}
    return {key: _read_curve(grid, key) for key, _ in CURVES}


def _protection_sheet(workbook: dict):
    wanted = names.normalize(names.sheet("protection"))
    for sheet, grid in workbook.items():
        if names.normalize(sheet) == wanted:
            return grid
    return None


def _read_curve(grid: list, key: str) -> list:
    voltage = _column(grid, names.anchor(f"{key}_voltage"))
    time = _column(grid, names.anchor(f"{key}_time"))
    if voltage is None or time is None:
        return []
    header_row, voltage_column = voltage
    _, time_column = time

    points = []
    for row in range(header_row + 1, len(grid)):
        at_voltage = wb._cell(grid, row, voltage_column)
        for_time = wb._cell(grid, row, time_column)
        if not at_voltage or not for_time:
            break
        points.append((float(at_voltage), float(for_time)))
    return points


def _column(grid: list, header: str) -> tuple | None:
    for row, cells in enumerate(grid):
        for column, value in enumerate(cells):
            if names.normalize(value).startswith(header):
                return row, column
    return None


def _parameter(params: list, name: str) -> str | None:
    for param in params:
        if param["name"].endswith(name):
            return str(param["value"])
    return None
