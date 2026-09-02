#!/usr/bin/env python3
# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""WECC front-end for the Excel -> DyCoV input generator: parsing + model resolution.

Reuses the stdlib ``.xlsx`` reader and the control-parameter parser (``workbook.py``),
and adds:
- ``read_selected_key``: the Excel-computed Model-Map key, read from the ``Général`` derived
  table (the tool has no knowledge of which blocks form the key);
- ``resolve_models``: that key -> Dynawo ``lib`` + prefix (per zone), by looking up the
  ``Model Map`` sheet;
- ``parse_zone``: the ``Zone1<x>`` / ``Zone3`` electrical tables, locating the *Valeurs* column
  per sheet (design doc section 4.3, the two sheets differ);
- ``parse_control_params``: the selected control parameters, flat, in workbook order;
- ``technology`` / ``template_for``: derive PV/BESS/Wind and the DyCoV template.

Everything here is the standard-specific front-end; the downstream is agnostic (design section 6).
"""

from __future__ import annotations

import sys
from pathlib import Path

# The parsing engine is a sibling top-level module; import it by path (repo tool convention).
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import workbook as wb  # noqa: E402

MODEL_MAP_SHEET = "Model Map"
_MAP_COLUMNS = ("zone3_lib", "zone3_prefix", "zone1_lib", "zone1_prefix")


# ---------------------------------------------------------------------------
# Model resolution (Général derived cells + Model Map sheet)
# ---------------------------------------------------------------------------


def _normalized_header(value) -> str | None:
    """``'Zone3_lib'`` / ``'Zone3 lib '`` -> ``'zone3 lib'`` (both spellings occur)."""
    if not isinstance(value, str) or not value.strip():
        return None
    return wb._strip_accents(value).replace("_", " ")


def _locate_key_column(grid) -> tuple[int, int] | None:
    """Return ``(header_row, key_col)`` of a model-map-shaped table in *grid*.

    Anchored on the ``Zone3 lib`` / ``Zone3_lib`` header cell; the key is the column
    immediately to its left, so the key header's own name is free to change.
    """
    for row_idx, row in enumerate(grid):
        for col, value in enumerate(row):
            if _normalized_header(value) == "zone3 lib" and col > 0:
                return row_idx, col - 1
    return None


def _config_grid(workbook: dict):
    """Return the ``Général`` sheet grid (accent-insensitive sheet-name match)."""
    for name, grid in workbook.items():
        if wb._strip_accents(name).startswith(wb._CONFIG_SHEET):
            return grid
    raise ValueError("Configuration sheet 'Général' not found in the workbook.")


def read_selected_key(workbook: dict) -> str:
    """Read the Excel-computed Model-Map key from the ``Général`` derived table.

    Excel computes the key from the block selection; the tool reads the cached cell verbatim
    and never reconstructs it (it has no knowledge of which blocks form the key).
    """
    grid = _config_grid(workbook)
    located = _locate_key_column(grid)
    if located is None:
        raise ValueError("derived-model table (header 'Zone3 lib') not found in 'Général'.")
    header_row, key_col = located
    key = wb._cell(grid, header_row + 1, key_col)
    if not key:
        raise ValueError(
            "the Model-Map key cell in 'Général' is empty: the workbook carries no cached "
            "formula values (it was saved by a tool other than Excel). Open the workbook in "
            "Excel and save it, then retry."
        )
    return key.strip()


def _read_model_map(workbook: dict) -> dict:
    """Read the ``Model Map`` table into ``{key -> {zone3_lib, zone3_prefix, zone1_lib,
    zone1_prefix}}`` (anchored on its ``Zone3_lib`` header, wherever the table sits)."""
    if MODEL_MAP_SHEET not in workbook:
        raise ValueError(f"'{MODEL_MAP_SHEET}' sheet not found in the workbook.")
    grid = workbook[MODEL_MAP_SHEET]
    located = _locate_key_column(grid)
    if located is None:
        raise ValueError(f"table header ('Zone3_lib' ...) not found in '{MODEL_MAP_SHEET}'.")
    header_row, key_col = located
    header = {_normalized_header(v): c for c, v in enumerate(grid[header_row])}
    cols = {
        name: header[name.replace("_", " ")]
        for name in _MAP_COLUMNS
        if name.replace("_", " ") in header
    }
    table = {}
    for r in range(header_row + 1, len(grid)):
        key = wb._cell(grid, r, key_col)
        if not key:
            break
        table[key.strip()] = {name: wb._cell(grid, r, cols[name]) for name in cols}
    return table


def resolve_models(workbook: dict) -> dict:
    """Resolve the selected variants to the Zone3 (plant) and Zone1 (turbine) ``lib`` + prefix.

    Returns ``{"key", "zone3_lib", "zone3_prefix", "zone1_lib", "zone1_prefix"}``. Raises if the
    key read from ``Général`` is not present in the ``Model Map`` (an unknown/unsupported model).
    """
    key = read_selected_key(workbook)
    table = _read_model_map(workbook)
    if key not in table:
        raise ValueError(
            f"variant combination not found in '{MODEL_MAP_SHEET}': {key!r}. Pick a combination "
            f"Dynawo has a model for in the 'Choix' column of 'Général', among: "
            f"{', '.join(sorted(table)) or '(none)'}"
        )
    return {"key": key, **table[key]}


# ---------------------------------------------------------------------------
# Technology / template
# ---------------------------------------------------------------------------


def technology(lib: str) -> str:
    """PV / BESS / Wind from a resolved model ``lib`` name."""
    if lib.startswith("Photovoltaics"):
        return "PV"
    if lib.startswith("BESS"):
        return "BESS"
    if lib.startswith(("WTG", "Wecc", "WT")):
        return "Wind"
    raise ValueError(f"cannot derive technology from lib {lib!r}")


def template_for(lib: str) -> str:
    """DyCoV input template for the resolved plant ``lib`` (``model_BESS`` / ``model_PPM``)."""
    return "model_BESS" if technology(lib) == "BESS" else "model_PPM"


# ---------------------------------------------------------------------------
# Electrical zone sheets (Zone1<x> / Zone3)
# ---------------------------------------------------------------------------


def _locate_param_table(grid) -> tuple[int, int, int]:
    """Return ``(header_row, name_col, value_col)`` of a zone sheet's parameter table.

    The two sheets differ (section 4.3): ``Zone1a`` has name/value in cols A/C, ``Zone3`` in
    B/D. Both are found by the header cells *Paramètres* and *Valeurs*.
    """
    for row_idx, row in enumerate(grid):
        header = {
            wb._strip_accents(v): c for c, v in enumerate(row) if isinstance(v, str) and v.strip()
        }
        if "valeurs" in header and ("parametres" in header or "parametre" in header):
            name_col = header.get("parametres", header.get("parametre"))
            return row_idx, name_col, header["valeurs"]
    raise ValueError("parameter table header ('Paramètres' / 'Valeurs') not found in the sheet.")


def parse_zone(workbook: dict, sheet_name: str) -> dict:
    """Parse a ``Zone1<x>`` / ``Zone3`` electrical table into ``{parameter name -> value}``.

    Values are strings (as read); an empty value stays ``None``. Reading stops at the first row
    with no parameter name (so trailing notes below the table are ignored).
    """
    if sheet_name not in workbook:
        raise ValueError(f"'{sheet_name}' sheet not found in the workbook.")
    grid = workbook[sheet_name]
    header_row, name_col, value_col = _locate_param_table(grid)
    values = {}
    for r in range(header_row + 1, len(grid)):
        name = wb._cell(grid, r, name_col)
        if not name:
            break
        values[name] = wb._cell(grid, r, value_col)
    return values


def zone1_sheets(workbook: dict) -> list:
    """Ordered list of ``Zone1<x>`` sheet names present (``Zone1a``, ``Zone1b``, ...)."""
    return [name for name in workbook if wb._strip_accents(name).startswith("zone1")]


# ---------------------------------------------------------------------------
# Control-block parameters
# ---------------------------------------------------------------------------


CONVERTER_VOLTAGE_CHOICE = "Un1 ou Un2"


def _normalized_number(text: str) -> str:
    """The shortest form that round-trips: Excel stores ``1e-5`` as ``1.0000000000000001E-5``."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return text
    if value.is_integer() and abs(value) < 1e16:
        return str(int(value))
    return repr(value)


def parse_control_params(workbook: dict, converter_voltage: str | None = None) -> list:
    """Selected control parameters, flat, in workbook order (sheet -> table -> parameter).

    Valued cells only. Each param is ``{"block"(provenance label, e.g. "REEC"), "name"(bare),
    "type"(mapped to the Dynawo convention), "value", "comments"}``; ``comments`` merges the
    per-parameter comment and base unit, and a variant's first param opens the section with the
    variant name. The flat order is what the PAR emits, so the Excel alone determines it.

    *converter_voltage* resolves the template's ``Un1 ou Un2`` base unit, which depends on the
    side the converter controls on, to the one actually in force.
    """
    config = wb.parse_config(workbook)
    variants = wb.parse_variants(workbook)
    result = []
    for block, variant in wb._selected_variants(config, variants):
        pending_section = [variant.name]
        for p in variant.parameters:
            if p.value is None:
                continue
            comments = pending_section
            pending_section = []
            merged = wb._merge_comment(p)
            if merged:
                if converter_voltage:
                    merged = merged.replace(CONVERTER_VOLTAGE_CHOICE, converter_voltage)
                comments.append(merged)
            param_type = wb._map_type(p.type)
            value = _normalized_number(p.value) if param_type == "DOUBLE" else p.value
            result.append(
                {"block": block, "name": p.name, "type": param_type,
                 "value": value, "comments": comments}
            )
    return result
