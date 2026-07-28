#!/usr/bin/env python3
# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""WECC front-end for the Excel -> DyCoV input generator: parsing + model resolution.

Reuses the stdlib ``.xlsx`` reader and the control-parameter parser from ``tools/dynawo_par``,
and adds:
- ``resolve_models``: the variant selection -> Dynawo ``lib`` + prefix (per zone), by looking up
  the ``Model Map`` sheet in Python (robust, independent of Excel's cached formula values);
- ``parse_zone``: the ``Zone1<x>`` / ``Zone3`` electrical tables, locating the *Valeurs* column
  per sheet (design doc section 4.3, the two sheets differ);
- ``parse_control_params``: the selected control blocks -> ``(bare name, type, value)``;
- ``technology`` / ``template_for``: derive PV/BESS/Wind and the DyCoV template.

Everything here is the standard-specific front-end; the downstream is agnostic (design section 6).
"""

from __future__ import annotations

import sys
from pathlib import Path

# The reader/parser live in the sibling tool; import them by path (repo tool convention).
_DYNAWO_PAR = Path(__file__).resolve().parent.parent / "dynawo_par"
if str(_DYNAWO_PAR) not in sys.path:
    sys.path.insert(0, str(_DYNAWO_PAR))

import generate_par as dp  # noqa: E402

# Blocks that form the Model-Map key, in the order used by the Excel formula
# (=TRIM(REGC)&"|"&TRIM(REEC)&"|"&TRIM(WTGT)&...): REGC|REEC|WTGT|WTGP|WTGA|WTGQ.
KEY_BLOCKS = ["REGC", "REEC", "WTGT", "WTGP", "WTGA", "WTGQ"]

MODEL_MAP_SHEET = "Model Map"
_MAP_COLUMNS = ("key", "zone3_lib", "zone3_prefix", "zone1_lib", "zone1_prefix")


# ---------------------------------------------------------------------------
# Model resolution (Model Map sheet)
# ---------------------------------------------------------------------------


def _read_model_map(workbook: dict) -> dict:
    """Read the ``Model Map`` table into ``{key -> {zone3_lib, zone3_prefix, zone1_lib,
    zone1_prefix}}`` (header located by its column names, wherever the table sits)."""
    if MODEL_MAP_SHEET not in workbook:
        raise ValueError(f"'{MODEL_MAP_SHEET}' sheet not found in the workbook.")
    grid = workbook[MODEL_MAP_SHEET]
    for row_idx, row in enumerate(grid):
        header = {
            v.strip().lower(): c for c, v in enumerate(row) if isinstance(v, str) and v.strip()
        }
        if "key" in header and "zone3_lib" in header:
            cols = {name: header[name] for name in _MAP_COLUMNS if name in header}
            table = {}
            for r in range(row_idx + 1, len(grid)):
                key = dp._cell(grid, r, cols["key"])
                if not key:
                    break
                table[key.strip()] = {
                    name: dp._cell(grid, r, cols[name]) for name in _MAP_COLUMNS[1:]
                }
            return table
    raise ValueError(f"table header ('Key' / 'Zone3_lib' ...) not found in '{MODEL_MAP_SHEET}'.")


def build_key(config) -> str:
    """Build the Model-Map lookup key from the block selection (``Général``)."""
    choices = {block: choice for block, choice in config.selections}
    return "|".join((choices.get(block) or "Aucun").strip() for block in KEY_BLOCKS)


def resolve_models(workbook: dict) -> dict:
    """Resolve the selected variants to the Zone3 (plant) and Zone1 (turbine) ``lib`` + prefix.

    Returns ``{"key", "zone3_lib", "zone3_prefix", "zone1_lib", "zone1_prefix"}``. Raises if the
    variant combination is not present in the ``Model Map`` (an unknown/unsupported model).
    """
    config = dp.parse_config(workbook)
    key = build_key(config)
    table = _read_model_map(workbook)
    if key not in table:
        raise ValueError(
            f"variant combination not found in '{MODEL_MAP_SHEET}': {key!r} "
            f"(known: {', '.join(sorted(table)) or '(none)'})"
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
            dp._strip_accents(v): c for c, v in enumerate(row) if isinstance(v, str) and v.strip()
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
        name = dp._cell(grid, r, name_col)
        if not name:
            break
        values[name] = dp._cell(grid, r, value_col)
    return values


def zone1_sheets(workbook: dict) -> list:
    """Ordered list of ``Zone1<x>`` sheet names present (``Zone1a``, ``Zone1b``, ...)."""
    return [name for name in workbook if dp._strip_accents(name).startswith("zone1")]


# ---------------------------------------------------------------------------
# Control-block parameters
# ---------------------------------------------------------------------------


def parse_control_params(workbook: dict) -> list:
    """Selected control blocks -> ``[(block, variant, params)]``, valued cells only.

    Each param is ``{"name"(bare), "type"(mapped to the Dynawo convention), "value", "comments"}``;
    ``comments`` merges the per-parameter comment/base unit and, on the block's first param, the
    ``[sheet, table | variant]`` section header (``dynawo_par`` design §8.3).
    """
    config = dp.parse_config(workbook)
    variants = dp.parse_variants(workbook)
    result = []
    for block, variant in dp._selected_variants(config, variants):
        params = []
        for p in variant.parameters:
            if p.value is None:
                continue
            comments = [variant.sheet, f"{variant.table} | {variant.name}"] if not params else []
            merged = dp._merge_comment(p)
            if merged:
                comments.append(merged)
            params.append(
                {"name": p.name, "type": dp._map_type(p.type), "value": p.value,
                 "comments": comments}
            )
        result.append((block, variant.name, params))
    return result
