#!/usr/bin/env python3
# Copyright (c) 2024-2026, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0
"""Generic Excel template parsing shared by the input-generation tools.

Standard library only: ``.xlsx`` files are plain ZIP archives of XML. This module holds the
workbook reader, the variant-table parser and the ``Général`` configuration parser — everything
that is template-format machinery rather than model semantics. It lives in ``dynawo_inputs``;
the legacy ``tools/dynawo_par`` imports it from here until that tool is retired.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# OpenXML spreadsheet namespaces.
_MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# Sheet names are matched accent-insensitively, hence the unaccented spelling.
_CONFIG_SHEET = "general"

# Choices in the configuration sheet that mean "no block selected".
_NO_BLOCK = {"", "aucun", "none", "n/a", "na", "-"}

# The template marks a parameter that does not apply to a variant, in its name cell or its value
# cell; written verbatim the mark would end up in the PAR.
_NOT_APPLICABLE = "/"

# Same idea in a base-unit or comment cell: the row has no annotation to carry.
_NO_ANNOTATION = {"-", "/", "n/a", "na"}

# Excel type -> Dynawo PAR type.
_TYPE_MAP = {
    "double": "DOUBLE",
    "float": "DOUBLE",
    "real": "DOUBLE",
    "boolean": "BOOL",
    "bool": "BOOL",
    "integer": "INT",
    "int": "INT",
    "string": "STRING",
    "str": "STRING",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Parameter:
    """A single parameter row of a variant table."""

    name: str
    type: str
    value: str | None = None
    comment: str | None = None
    base_unit: str | None = None


@dataclass
class Columns:
    """The columns a variant's parameters are read from; ``base``/``comment`` are optional."""

    param: int
    value: int
    type: int
    base: int | None = None
    comment: int | None = None


@dataclass
class Variant:
    """One variant (column group) of a table, e.g. ``REEC_A``."""

    name: str
    sheet: str
    table: str
    parameters: list[Parameter] = field(default_factory=list)


@dataclass
class Config:
    """Parsed contents of the ``Général`` configuration sheet."""

    # Ordered list of (block type, chosen variant), e.g. ("REEC", "REEC_A").
    selections: list[tuple[str, str]] = field(default_factory=list)
    # Zones each block declares, e.g. {"REEC": ["Zone1", "Zone3"]}; empty when
    # the sheet has no ``Zone`` column.
    zones: dict[str, list[str]] = field(default_factory=dict)
    sn_zone1: str | None = None
    sn_zone3: str | None = None
    n_converters: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_accents(text: str) -> str:
    """Return *text* lower-cased and stripped of diacritics, for matching."""
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c)).strip().lower()


def _col_letters_to_index(ref: str) -> int:
    """Convert a cell/column reference (e.g. ``"AB12"``) to a 0-based column."""
    match = re.match(r"([A-Za-z]+)", ref)
    letters = match.group(1).upper()
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return col - 1


# ---------------------------------------------------------------------------
# XLSX reading (standard library only)
# ---------------------------------------------------------------------------

# A sheet grid: list of rows, each row a list of cell values (str or None).
Grid = list[list["str | None"]]


def read_workbook(path: Path) -> dict[str, Grid]:
    """Read every worksheet of *path* into an ordered ``{name: grid}`` mapping.

    Cell values are returned as strings (or ``None`` when empty). No type
    conversion is applied beyond rendering booleans as ``true``/``false``.
    """
    with zipfile.ZipFile(path) as archive:
        shared = _read_shared_strings(archive)
        sheets = _read_sheet_index(archive)
        return {
            name: _read_sheet_grid(archive, target, shared)
            for name, target in sheets
        }


def _read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Return the shared-strings table (an empty list when absent)."""
    name = "xl/sharedStrings.xml"
    if name not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(name))
    strings: list[str] = []
    for si in root.findall(f"{_MAIN_NS}si"):
        strings.append("".join(t.text or "" for t in si.iter(f"{_MAIN_NS}t")))
    return strings


def _read_sheet_index(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return ordered ``(sheet_name, worksheet_path)`` pairs."""
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))

    rid_to_target: dict[str, str] = {}
    for rel in rels:
        target = rel.get("Target", "")
        # Targets are either absolute ("/xl/worksheets/sheet1.xml", written by
        # openpyxl) or relative to the workbook part ("worksheets/sheet1.xml").
        target = target.lstrip("/") if target.startswith("/") else "xl/" + target
        rid_to_target[rel.get("Id")] = target

    sheets: list[tuple[str, str]] = []
    for sheet in workbook.iter(f"{_MAIN_NS}sheet"):
        rid = sheet.get(f"{_REL_NS}id")
        target = rid_to_target.get(rid)
        if target:
            sheets.append((sheet.get("name", ""), target))
    return sheets


def _read_sheet_grid(
    archive: zipfile.ZipFile, target: str, shared: list[str]
) -> Grid:
    """Parse a single worksheet XML into a dense grid of string values."""
    root = ET.fromstring(archive.read(target))
    cells: dict[tuple[int, int], str] = {}
    max_row = max_col = -1

    for cell in root.iter(f"{_MAIN_NS}c"):
        ref = cell.get("r")
        if not ref:
            continue
        row = int(re.search(r"\d+", ref).group()) - 1
        col = _col_letters_to_index(ref)
        value = _cell_value(cell, shared)
        if value is None or value == "":
            continue
        cells[(row, col)] = value
        max_row = max(max_row, row)
        max_col = max(max_col, col)

    grid: Grid = [[None] * (max_col + 1) for _ in range(max_row + 1)]
    for (row, col), value in cells.items():
        grid[row][col] = value
    return grid


def _cell_value(cell: ET.Element, shared: list[str]) -> str | None:
    """Return the textual value of a worksheet cell."""
    ctype = cell.get("t")
    if ctype == "s":  # shared string
        node = cell.find(f"{_MAIN_NS}v")
        return shared[int(node.text)] if node is not None else None
    if ctype == "inlineStr":  # inline string
        node = cell.find(f"{_MAIN_NS}is")
        return "".join(t.text or "" for t in node.iter(f"{_MAIN_NS}t")) if node is not None else None
    if ctype == "b":  # boolean -> Dynawo wants true/false
        node = cell.find(f"{_MAIN_NS}v")
        return "true" if (node is not None and node.text == "1") else "false"
    # number, date, or formula result: keep the literal text as-is.
    node = cell.find(f"{_MAIN_NS}v")
    return node.text if node is not None else None


def _cell(grid: Grid, row: int, col: int) -> str | None:
    """Safe accessor that returns ``None`` when the cell is out of range."""
    if 0 <= row < len(grid) and 0 <= col < len(grid[row]):
        value = grid[row][col]
        return value.strip() if isinstance(value, str) else value
    return None


# ---------------------------------------------------------------------------
# Parameter table parsing
# ---------------------------------------------------------------------------


def parse_variants(workbook: dict[str, Grid]) -> dict[str, Variant]:
    """Parse every structured parameter sheet into variants keyed by name.

    Descriptive sheets (no ``Parameter | Type | Value`` header) and the
    configuration sheet yield nothing and are therefore ignored automatically.
    """
    variants: dict[str, Variant] = {}
    for sheet_name, grid in workbook.items():
        if _strip_accents(sheet_name).startswith(_CONFIG_SHEET):
            continue
        for variant in _parse_sheet(sheet_name, grid):
            if variant.name in variants:
                raise ValueError(
                    f"Duplicate variant '{variant.name}' found in sheets "
                    f"'{variants[variant.name].sheet}' and '{sheet_name}'."
                )
            variants[variant.name] = variant
    return variants


def _parse_sheet(sheet_name: str, grid: Grid) -> list[Variant]:
    """Parse the (single) parameter table block of one sheet into variants."""
    header_row = _find_header_row(grid)
    if header_row is None:
        return []  # not a structured parameter sheet

    column_groups = _find_column_groups(grid, header_row)
    base_columns = _find_extra_columns(grid, header_row, "base")
    comment_columns = _find_extra_columns(grid, header_row, "comment")
    table_labels = _find_table_labels(grid, header_row - 2)

    variants: list[Variant] = []
    for param_col in sorted(column_groups):
        variant_name = _cell(grid, header_row - 1, param_col)
        columns = _group_columns(grid, header_row, param_col, table_labels)
        if not variant_name or columns is None:
            continue
        columns.base = _extra_for_column(base_columns, table_labels, param_col)
        columns.comment = _extra_for_column(comment_columns, table_labels, param_col)
        variant = Variant(
            name=variant_name,
            sheet=sheet_name,
            table=_label_for_column(table_labels, param_col) or sheet_name,
        )
        variant.parameters = _parse_parameters(grid, header_row, columns)
        variants.append(variant)
    return variants


_PARAM_HEADER_PREFIXES = ("parametre", "parameter")
_TYPE_HEADERS = {"type", "types"}
_VALUE_HEADERS = {"value", "values", "valeur", "valeurs"}


def _normalized_header(value) -> str:
    """Header text lower-cased, accent-free and single-spaced (``""`` when not text)."""
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", _strip_accents(value))


def _is_param_header(value) -> bool:
    """True for ``Paramètres``/``Parameter``, with any suffix such as ``(Dynawo)``."""
    return _normalized_header(value).startswith(_PARAM_HEADER_PREFIXES)


def _is_type_header(value) -> bool:
    return _normalized_header(value) in _TYPE_HEADERS


def _is_value_header(value) -> bool:
    return _normalized_header(value) in _VALUE_HEADERS


def _heads_parameter_table(row: list) -> bool:
    """True when *row* heads a parameter table: it names parameters, values and types.

    Requiring all three keeps non-table uses of the word out (e.g. the zone sheets'
    ``Paramètres | Descriptions | Valeurs`` electrical tables).
    """
    return (
        any(_is_param_header(value) for value in row)
        and any(_is_value_header(value) for value in row)
        and any(_is_type_header(value) for value in row)
    )


def _find_header_row(grid: Grid) -> int | None:
    """Return the first row index that heads a parameter table."""
    for row_idx, row in enumerate(grid):
        if _heads_parameter_table(row):
            return row_idx
    return None


def _find_column_groups(grid: Grid, header_row: int) -> list[int]:
    """Return the column index of every variant column group in the header row."""
    return [col for col, value in enumerate(grid[header_row]) if _is_param_header(value)]


def _group_columns(
    grid: Grid, header_row: int, param_col: int, labels: list[tuple[int, str]]
) -> "Columns | None":
    """Return the columns of the variant group starting at *param_col*, ``None`` if incomplete.

    Value and type are the nearest such headers to the right of *param_col*, within its table
    block: adjacent when the variant carries its own ``Types`` column (``Parameter | Type |
    Value``), further right when the block's variants share a single one (``Parameter | Value``
    repeated).
    """
    _, block_end = _block_bounds(labels, param_col)

    def nearest(matches) -> int | None:
        return next(
            (
                col
                for col, value in enumerate(grid[header_row])
                if param_col < col < block_end and matches(value)
            ),
            None,
        )

    value_col, type_col = nearest(_is_value_header), nearest(_is_type_header)
    if value_col is None or type_col is None:
        return None
    return Columns(param=param_col, value=value_col, type=type_col)


def _find_extra_columns(grid: Grid, header_row: int, prefix: str) -> list[int]:
    """Return header columns whose label starts with *prefix* (case-insensitive).

    Used for the optional ``Base unit`` / ``Base`` and ``Comment`` columns.
    """
    return [
        col
        for col, value in enumerate(grid[header_row])
        if isinstance(value, str) and value.strip().lower().startswith(prefix)
    ]


def _find_table_labels(grid: Grid, label_row: int) -> list[tuple[int, str]]:
    """Return sorted ``(column, label)`` table names from the label row."""
    if label_row < 0 or label_row >= len(grid):
        return []
    return sorted(
        (col, value.strip())
        for col, value in enumerate(grid[label_row])
        if isinstance(value, str) and value.strip()
    )


def _label_for_column(labels: list[tuple[int, str]], col: int) -> str | None:
    """Return the table label governing *col* (nearest label at or left of it)."""
    chosen: str | None = None
    for label_col, label in labels:
        if label_col <= col:
            chosen = label
        else:
            break
    return chosen


def _block_bounds(labels: list[tuple[int, str]], col: int) -> tuple[int, float]:
    """Return the ``[start, end)`` column span of the table block holding *col*."""
    block_start = 0
    block_end = float("inf")
    for label_col, _ in labels:
        if label_col <= col:
            block_start = label_col
        elif label_col < block_end:
            block_end = label_col
    return block_start, block_end


def _extra_for_column(
    extra_columns: list[int], labels: list[tuple[int, str]], param_col: int
) -> int | None:
    """Return the extra column (base unit / comment) of *param_col*'s block."""
    block_start, block_end = _block_bounds(labels, param_col)
    for extra_col in extra_columns:
        if block_start <= extra_col < block_end:
            return extra_col
    return None


def _parse_parameters(grid: Grid, header_row: int, columns: Columns) -> list[Parameter]:
    """Parse the data rows of a single variant column group.

    A row is valid for this variant when both ``Parameter`` and ``Type`` are
    non-empty. Empty rows (for this variant) are skipped without ending the
    table, so sparse parallel variants are handled correctly.
    """
    def annotation(row: int, col: int | None) -> str | None:
        text = _cell(grid, row, col) if col is not None else None
        return text if text and text.casefold() not in _NO_ANNOTATION else None

    parameters: list[Parameter] = []
    for row in range(header_row + 1, len(grid)):
        name = _cell(grid, row, columns.param)
        ptype = _cell(grid, row, columns.type)
        if not name or not ptype or name == _NOT_APPLICABLE:
            continue
        value = _cell(grid, row, columns.value)
        if value == _NOT_APPLICABLE:
            value = None
        base_unit = annotation(row, columns.base)
        comment = annotation(row, columns.comment)
        parameters.append(
            Parameter(
                name=name,
                type=ptype,
                value=value if value else None,
                comment=comment if comment else None,
                base_unit=base_unit if base_unit else None,
            )
        )
    return parameters


# ---------------------------------------------------------------------------
# Configuration sheet parsing
# ---------------------------------------------------------------------------


def parse_config(workbook: dict[str, Grid]) -> Config:
    """Parse the ``Général`` sheet for block selections and global parameters."""
    for sheet_name, grid in workbook.items():
        if _strip_accents(sheet_name).startswith(_CONFIG_SHEET):
            config = Config()
            config.selections, config.zones = _parse_block_selection(grid)
            _parse_globals(grid, config)
            return config
    raise ValueError("Configuration sheet 'Général' not found in the workbook.")


def _header_column(row: list, name: str) -> int | None:
    """Column of the header cell matching *name* (accent/case-insensitive)."""
    return next(
        (c for c, v in enumerate(row) if isinstance(v, str) and _strip_accents(v) == name),
        None,
    )


def _parse_block_selection(
    grid: Grid,
) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
    """Read the ``Type de bloc | Choix`` table into ordered (block, choice).

    Also returns the per-block zone declarations from the optional ``Zone``
    column (``;``-separated, e.g. ``"Zone1;Zone3"``); when the column is
    absent the zones mapping is empty.
    """
    for row_idx, row in enumerate(grid):
        normalized = [_strip_accents(c) for c in row if isinstance(c, str)]
        if "type de bloc" in normalized and "choix" in normalized:
            block_col = _header_column(row, "type de bloc")
            choice_col = _header_column(row, "choix")
            zone_col = _header_column(row, "zone")
            selections: list[tuple[str, str]] = []
            zones: dict[str, list[str]] = {}
            for r in range(row_idx + 1, len(grid)):
                block = _cell(grid, r, block_col)
                if not block:
                    break
                choice = _cell(grid, r, choice_col) or ""
                selections.append((block, choice))
                if zone_col is not None:
                    declared = _cell(grid, r, zone_col) or ""
                    zones[block] = [z.strip() for z in declared.split(";") if z.strip()]
            return selections, zones
    raise ValueError(
        "Block-selection table ('Type de bloc' | 'Choix') not found in 'Général'."
    )


def _parse_globals(grid: Grid, config: Config) -> None:
    """Read SnZone1, SnZone3 and the converter count from the globals table."""
    for row_idx, row in enumerate(grid):
        normalized = [_strip_accents(c) for c in row if isinstance(c, str)]
        if "grandeur" in normalized and "valeur" in normalized:
            name_col = next(
                c for c, v in enumerate(row)
                if isinstance(v, str) and _strip_accents(v) == "grandeur"
            )
            value_col = next(
                c for c, v in enumerate(row)
                if isinstance(v, str) and _strip_accents(v) == "valeur"
            )
            for r in range(row_idx + 1, len(grid)):
                name = _cell(grid, r, name_col)
                if not name:
                    break
                value = _cell(grid, r, value_col)
                key = _strip_accents(name)
                if key == "snzone1":
                    config.sn_zone1 = value
                elif key == "snzone3":
                    config.sn_zone3 = value
                elif "convertisseur" in key or "converter" in key:
                    config.n_converters = value
            return
    # The globals table is optional; absence simply leaves the fields as None.


# ---------------------------------------------------------------------------
# Shared selection / rendering helpers
# ---------------------------------------------------------------------------


def _map_type(excel_type: str) -> str:
    """Map an Excel type to the Dynawo PAR convention (unknown -> upper-case)."""
    return _TYPE_MAP.get(excel_type.strip().lower(), excel_type.strip().upper())


def _merge_comment(param: Parameter) -> str | None:
    """Merge the optional comment and base unit into a single comment string."""
    parts = []
    if param.comment:
        parts.append(param.comment)
    if param.base_unit:
        parts.append(f"Base unit: {param.base_unit}")
    return " | ".join(parts) if parts else None


def _selected_variants(
    config: Config, variants: dict[str, Variant]
) -> list[tuple[str, Variant]]:
    """Return the enabled ``(block, variant)`` pairs in *workbook* order.

    The ``Général`` sheet only decides *which* variant each block uses; the
    output order follows the sheets and tables of the Excel file (the insertion
    order of *variants*), as required by the order-preservation principle.
    Disabled blocks (``Aucun`` / empty) are skipped; a selected variant that is
    absent from every parameter sheet raises an explicit error.
    """
    block_of: dict[str, str] = {}
    for block, choice in config.selections:
        if _strip_accents(choice) in _NO_BLOCK:
            continue
        if choice not in variants:
            found = ", ".join(sorted(variants)) or "(none — the parameter sheets look unfilled)"
            raise ValueError(
                f"Selected variant '{choice}' (block '{block}') has no parameter table in the "
                f"workbook: expected '{choice}' right above a 'Parameter' column header, "
                f"typically in the '{block}' sheet. Variant tables found: {found}."
            )
        block_of[choice] = block
    return [
        (block_of[name], variant)
        for name, variant in variants.items()
        if name in block_of
    ]
